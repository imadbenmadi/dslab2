import * as THREE from 'https://esm.sh/three@0.160.0';

const COL = { bg:0x0b0e13, ground:0x0f141a, road:0x1c232c, dash:0x3a4552, dome:0x7f9bb8, anchor:0xff6fa8, serving:0x4da3ff, exec:0x3ddc84, car:0xffd23f, broker:0x9aa3ad, task:0x4da3ff, result:0x3ddc84, ack:0xffd23f, state:0x8a94a3, dead:0x3a4049, wan:0x6fc3d9, hot:0xff4545, link:0x5f6b78, led:0x1c2b24 };
const H6 = n => '#' + n.toString(16).padStart(6, '0');
const ZDEF = [
  { id:'Z1', x:-18, z:0, r:8.5, side:-1 },
  { id:'Z2', x:-5, z:0, r:9, side:1 },
  { id:'Z3', x:18, z:0, r:8, side:-1 },
  { id:'Z4', x:12, z:-16, r:9, side:1 },
  { id:'Z5', x:-17, z:-16, r:7.5, side:-1, late:true },
];
const NEIGH = { Z1:['Z2','Z5',null,null], Z2:['Z1','Z3','Z4','Z5'], Z3:['Z2','Z4',null,null], Z4:['Z3','Z2','Z5',null], Z5:['Z1','Z4','Z2',null] };
const PEERS = [['Z1','Z2'],['Z1','Z5'],['Z2','Z3'],['Z2','Z4'],['Z2','Z5'],['Z3','Z4'],['Z4','Z5']];
const RING = [[-28,0],[28,0],[28,-16],[-28,-16]], RL = 144;
const BROKER = { x:2, z:-8 }, CLOUD_Y = 27, HERO = 7;
const SANS = "'IBM Plex Sans', sans-serif", MONO = "'IBM Plex Mono', monospace";
const PCOL = { task:COL.task, result:COL.result, ack:COL.ack, state:COL.state };

function ringPos(s, lane) {
  s = ((s % RL) + RL) % RL;
  for (let i = 0; i < 4; i++) {
    const a = RING[i], b = RING[(i + 1) % 4], L = Math.hypot(b[0]-a[0], b[1]-a[1]);
    if (s <= L) { const dx = (b[0]-a[0])/L, dz = (b[1]-a[1])/L; return { x:a[0]+dx*s - dz*lane, z:a[1]+dz*s + dx*lane, dx, dz }; }
    s -= L;
  }
  return { x:-28, z:0, dx:1, dz:0 };
}
const equip = z => ({ x:z.x, z:z.z + z.side*3.4 });
const kind = id => id.split(':')[0];
const isWan = (a,b) => (a==='broker'&&b==='cloud')||(a==='cloud'&&b==='broker');

function along(pts, t, d) {
  if (pts.length === 2) return [pts[0], pts[1], t];
  const ls = []; let L = 0;
  for (let i = 0; i < pts.length-1; i++) { const v = d(pts[i], pts[i+1]); ls.push(v); L += v; }
  let r = t*L;
  for (let i = 0; i < ls.length; i++) { if (r <= ls[i] || i === ls.length-1) return [pts[i], pts[i+1], ls[i] ? Math.min(1, r/ls[i]) : 0]; r -= ls[i]; }
}

export async function createPCNME(root, cb = {}) {
  const call = (k, ...a) => { try { cb[k] && cb[k](...a); } catch (e) { console.error(e); } };
  root.innerHTML = '';
  const S = { insets:{ left:0, right:0, top:64, bottom:44 }, speed:1, ambient:true, radio:true, zones:{}, cars:[], packets:[], timers:[], waiters:[], tags:[], fx:[], wanLoad:0, wanMs:50, cloudSlots:new Array(24).fill(0), flowActive:false, sel:null, ambT:1, cloudT:2 };
  ZDEF.forEach(d => S.zones[d.id] = { ...d, alive:true, joined:!d.late, fade:d.late?0:1, slots:[0,0,0,0], queue:0, held:false, roles:new Set() });
  const SPEC = [[1,10,1,2.6],[2,40,-1,2.9],[3,64,1,2.3],[4,90,-1,2.7],[5,112,1,3.0],[6,130,-1,2.4],[7,3,1,2.5],[8,80,1,2.8],[9,22,-1,2.2],[10,100,-1,2.6]];
  S.cars = SPEC.map(([id,s,dir,v]) => ({ id, s, dir, v, v0:v, serv:null }));
  const CAR = {}; S.cars.forEach(c => CAR[c.id] = c);
  const hero = CAR[HERO];
  const carPos = c => ringPos(c.s, c.dir > 0 ? 0.8 : -0.8);
  function serving(c) {
    const p = carPos(c);
    if (p.x > 4.5 && p.x < 10.5 && Math.abs(p.z) < 2.5) return null;
    let best = null, bd = 1e9;
    for (const z of Object.values(S.zones)) {
      if (!z.alive || !z.joined) continue;
      const d = Math.hypot(p.x-z.x, p.z-z.z);
      if (d <= z.r && d < bd) { bd = d; best = z.id; }
    }
    return best;
  }
  S.cars.forEach(c => c.serv = serving(c));
  const servOf = id => CAR[id].serv;

  // ---------- engine ----------
  const simWait = s => new Promise(res => S.timers.push({ t:s, res }));
  const simUntil = f => new Promise(res => S.waiters.push({ f, res }));
  function segDur(a, b) {
    if (isWan(a,b)) return Math.min(3.4, 1.3*(1 + S.wanLoad*0.12));
    const ka = kind(a), kb = kind(b);
    if (ka==='car'||kb==='car') return .6;
    if (ka==='ap'||kb==='ap') return .25;
    return .6;
  }
  const fx = (id, color) => S.fx.push({ id, color, t:0 });
  function enterSeg(p) {
    const i = p.seg + 1;
    if (typeof p.ids[i] === 'function') p.ids[i] = p.ids[i]();
    if (!p.ids[i]) { fx(p.ids[p.seg], COL.hot); return false; }
    p.wan = isWan(p.ids[p.seg], p.ids[i]);
    if (p.wan) S.wanLoad++;
    p.dur = segDur(p.ids[p.seg], p.ids[i]); p.t = 0;
    return true;
  }
  function send(type, ids, o = {}) {
    return new Promise(res => {
      const p = { type, ids:ids.slice(), seg:0, t:0, dur:1, done:res, size:o.size||1, faint:!!o.faint, from:o.from };
      if (typeof p.ids[0] === 'function') p.ids[0] = p.ids[0]();
      if (!enterSeg(p)) { res(false); return; }
      S.packets.push(p);
    });
  }
  function killP(p, ok) { const i = S.packets.indexOf(p); if (i >= 0) S.packets.splice(i, 1); if (p.wan) { S.wanLoad--; p.wan = false; } p.done(ok); }
  function toCar(id) { let z; return [() => { z = servOf(id); return z ? 'fog:'+z : null; }, () => 'ap:'+z, 'car:'+id]; }

  function step(dt) {
    const sdt = dt * S.speed;
    for (const c of S.cars) { c.s += c.dir*c.v*sdt; c.serv = serving(c); }
    for (const t of S.timers.slice()) { t.t -= sdt; if (t.t <= 0) { S.timers.splice(S.timers.indexOf(t), 1); t.res(); } }
    for (const w of S.waiters.slice()) if (w.f()) { S.waiters.splice(S.waiters.indexOf(w), 1); w.res(); }
    for (const p of S.packets.slice()) {
      p.t += sdt / p.dur;
      if (p.t >= 1) {
        if (p.wan) { S.wanLoad--; p.wan = false; }
        p.seg++;
        if (p.seg >= p.ids.length-1) killP(p, true);
        else if (!enterSeg(p)) killP(p, false);
      }
    }
    for (const z of Object.values(S.zones)) {
      z.slots = z.slots.map(v => Math.max(0, v - sdt));
      z.fade += ((z.joined ? 1 : 0) - z.fade) * Math.min(1, dt*2.5);
    }
    S.cloudSlots = S.cloudSlots.map(v => Math.max(0, v - sdt));
    S.tags = S.tags.filter(t => (t.ttl -= sdt) > 0 || (t.el && t.el.remove(), false));
    S.fx = S.fx.filter(f => (f.t += dt) < 0.9);
    const target = 50 + Math.min(150, Math.max(0, S.wanLoad)*16);
    S.wanMs += (target - S.wanMs) * Math.min(1, dt*2);
    if (S.ambient) {
      S.ambT -= sdt; S.cloudT -= sdt;
      if (S.ambT <= 0) {
        S.ambT = .55 + Math.random()*.6;
        const zs = Object.values(S.zones).filter(z => z.alive && z.joined);
        const z = zs[Math.floor(Math.random()*zs.length)];
        if (z) {
          if (Math.random() < .6) send('state', ['fog:'+z.id, 'broker'], { faint:true, size:.6 });
          else send('state', ['broker', 'fog:'+z.id], { faint:true, size:.6, from:'cloud' });
        }
      }
      if (S.cloudT <= 0) { S.cloudT = 2.5 + Math.random()*2; send('state', ['cloud','broker'], { faint:true, size:.6 }); }
    }
  }

  // ---------- flows ----------
  let tok = { dead:true };
  const CANCEL = {};
  function reset() {
    tok.dead = true;
    S.packets.slice().forEach(p => killP(p, false)); S.packets = [];
    S.timers.splice(0).forEach(t => t.res());
    S.waiters.splice(0).forEach(w => w.res());
    S.tags.forEach(t => t.el && t.el.remove()); S.tags = [];
    S.wanLoad = 0; S.cloudSlots.fill(0);
    for (const z of Object.values(S.zones)) { z.alive = true; if (z.late && z.joined) { z.joined = false; } z.roles.clear(); z.slots = [0,0,0,0]; z.queue = 0; z.held = false; }
    hero.v = hero.v0; S.flowActive = false;
    call('onDecision', null); call('onFlow', null);
  }

  async function runFlow(n) {
    reset();
    const my = { dead:false }; tok = my;
    S.flowActive = true; call('onFlow', n); call('onClear');
    const ck = () => { if (my.dead) throw CANCEL; };
    const X = {
      wait: async s => { await simWait(s); ck(); },
      until: async f => { await simUntil(f); ck(); },
      send: async (t, ids, o) => { const r = await send(t, ids, o); ck(); return r; },
      fan: async (t, lists, o) => { const r = await Promise.all(lists.map(ids => send(t, ids, o))); ck(); return r; },
      exec: async (node, d) => { const arr = node==='cloud' ? S.cloudSlots : S.zones[node].slots; let i = arr.findIndex(v => v <= 0); if (i < 0) i = 0; arr[i] = d; await simWait(d); ck(); },
      busy: (node, k, d, q) => { const z = S.zones[node]; for (let i = 0; i < k; i++) z.slots[i] = Math.max(z.slots[i], d); z.queue = q || 0; simWait(d).then(() => z.queue = 0); },
      role: (z, r) => S.zones[z].roles.add(r),
      unrole: (z, r) => S.zones[z].roles.delete(r),
      hero: (x, v) => { hero.s = x + 28; hero.v = v; hero.serv = serving(hero); },
      speed: v => hero.v = v,
      tag: (id, text, color, ttl = 3) => S.tags.push({ id, text, color:H6(color), ttl }),
      log: (t, k) => call('onLog', { text:t, kind:k || 'info' }),
      decide: (zone, qs, chosen, note) => {
        const nb = NEIGH[zone];
        const opts = ['here','n1','n2','n3','n4','cloud'].map((k, i) => {
          const target = k==='here' ? zone : k==='cloud' ? 'Cloud' : nb[i-1];
          let masked = false, why = '';
          if (k[0]==='n') {
            if (!target) { masked = true; why = 'no neighbour'; }
            else { const t = S.zones[target]; if (!t.joined) { masked = true; why = 'not joined'; } else if (!t.alive) { masked = true; why = 'offline'; } }
          }
          const label = k==='here' ? 'here · '+zone : k==='cloud' ? 'cloud' : 'N'+i+' · '+(target||'—');
          return { key:k, label, target, q:masked?0:(qs[k] ?? 0.2), masked, why, chosen:k===chosen };
        });
        call('onDecision', { zone, note, options:opts });
        const o = opts.find(o => o.chosen);
        if (o) X.tag('fog:'+zone, 'D3QN → '+o.target, COL.exec, 3.5);
      },
    };
    const up = z => ['car:'+HERO, 'ap:'+z, 'fog:'+z];
    const ackPath = anchor => { const s = servOf(HERO); if (!s) return null; return s===anchor ? ['car:'+HERO,'ap:'+s,'fog:'+s] : ['car:'+HERO,'ap:'+s,'fog:'+s,'broker','fog:'+anchor]; };
    const FL = {
      1: async () => {
        X.hero(-25, .6); X.busy('Z1', 3, 7, 2);
        await X.wait(.4);
        X.log('Car 7 captures a camera frame → YOLO detection task (hard deadline 150 ms). Sent by radio to the zone it is in.', 'task');
        X.role('Z1', 'anchor');
        await X.send('task', up('Z1'));
        X.log('Z1 becomes the anchor. TOF-Broker: 2.1 GFLOP, below the heavy-task threshold → hand to the D3QN agent.');
        X.tag('fog:Z1', 'TOF-Broker → D3QN', COL.anchor, 2);
        await X.wait(.9);
        X.decide('Z1', { here:.46, n1:.81, cloud:.33 }, 'n1', 'Z1 queue is busy (3/4 slots). Neighbour Z2 is idle and 2 ms away.');
        X.log('D3QN picks neighbour Z2. The whole task moves over backhaul — it runs on exactly one node.', 'task');
        await X.wait(.6);
        X.role('Z2', 'exec');
        await X.send('task', ['fog:Z1','fog:Z2']);
        X.log('Z2 runs the task in a free execution slot.', 'info');
        await X.exec('Z2', 1.6);
        X.log('Z2 publishes car/7/result → broker → the zone serving car 7 (Z1). The anchor role is not on the result path — Z1 just happens to serve the car.', 'result');
        await X.send('result', ['fog:Z2','broker', ...toCar(HERO)]);
        X.log('Car 7 receives the result over radio and acks the anchor.', 'ack');
        const ap = ackPath('Z1'); if (ap) await X.send('ack', ap);
        X.tag('fog:Z1', 'reward r = +0.82 · 94 ms', COL.ack, 3.5);
        X.log('Anchor Z1 computes the reward (deadline met, 94 ms) and stores the experience for D3QN.', 'done');
        await X.wait(1);
      },
      2: async () => {
        X.hero(-17, 1.7);
        await X.wait(.3);
        X.log('Car 7 heads east, out of Z1, and sends a task.', 'task');
        X.role('Z1', 'anchor');
        await X.send('task', up('Z1'));
        X.tag('fog:Z1', 'mobility: leaves Z1 in ~2 s', COL.anchor, 2.5);
        X.log('Mobility predictor (GPS every 100 ms): car 7 will leave Z1 in about 2 s.');
        await X.wait(.7);
        X.decide('Z1', { here:.38, n1:.52, cloud:.74 }, 'cloud', 'Car is leaving Z1; the cloud has free slots and the WAN is quiet.');
        const handover = (async () => {
          await X.until(() => servOf(HERO) === 'Z2');
          X.log('Car 7 enters Z2. Z2 publishes car/7/attach and subscribes to car/7/result.', 'state');
          X.tag('fog:Z2', 'attach car/7', COL.serving, 3);
          X.speed(.8);
          await X.send('state', ['fog:Z2','broker']);
        })();
        X.log('Task travels to the cloud over the WAN (50–200 ms).', 'task');
        await X.send('task', ['fog:Z1','broker','cloud']);
        await X.exec('cloud', 1.0);
        await handover;
        X.log('Cloud publishes car/7/result once. Broker delivers it to Z2 (serving) and a copy to anchor Z1.', 'result');
        await X.send('result', ['cloud','broker']);
        X.tag('fog:Z1', 'copy (anchor)', COL.result, 2.5);
        await X.fan('result', [['broker', ...toCar(HERO)], ['broker','fog:Z1']], { from:'cloud' });
        X.log('Car 7 acks through Z2 → broker → anchor Z1.', 'ack');
        const ap = ackPath('Z1'); if (ap) await X.send('ack', ap);
        X.tag('fog:Z1', 'reward r = +0.64 · 138 ms', COL.ack, 3.5);
        X.log('Anchor Z1 computes the reward. Handover cost no extra work — the per-car topic found the car.', 'done');
        await X.wait(1);
      },
      3: async () => {
        X.hero(-3, 2.0);
        await X.wait(.3);
        X.log('Car 7 sends a soft-deadline task (400 ms) just before the tunnel.', 'task');
        X.role('Z2', 'anchor');
        await X.send('task', up('Z2'));
        await X.wait(.5);
        X.decide('Z2', { here:.77, n1:.41, n2:.55, n3:.38, cloud:.29 }, 'here', 'Z2 has free slots — run it here.');
        X.role('Z2', 'exec');
        await X.exec('Z2', 1.2);
        await X.until(() => servOf(HERO) === null);
        X.log('Z2 publishes car/7/result — but car 7 is in the tunnel. No zone serves it, so nothing is delivered.', 'warn');
        await X.send('result', ['fog:Z2','broker', ...toCar(HERO)]);
        S.zones.Z2.held = true;
        X.tag('fog:Z2', 'holding result for car 7', COL.anchor, 30);
        X.log('Anchor Z2 keeps a copy and waits for the car to reappear.');
        await X.until(() => servOf(HERO) === 'Z3');
        X.speed(1.1);
        X.log('Car 7 comes out in Z3. Z3 publishes car/7/attach.', 'state');
        X.tag('fog:Z3', 'attach car/7', COL.serving, 3);
        await X.send('state', ['fog:Z3','broker','fog:Z2']);
        S.tags = S.tags.filter(t => t.text !== 'holding result for car 7' || (t.el && t.el.remove(), false));
        S.zones.Z2.held = false;
        X.log('Anchor Z2 republishes the held result → broker → Z3 → car 7.', 'result');
        await X.send('result', ['fog:Z2','broker', ...toCar(HERO)]);
        const ap = ackPath('Z2'); if (ap) await X.send('ack', ap);
        X.log('Delivered in 312 ms, inside the soft deadline. A hard task past its deadline would have been dropped instead.', 'done');
        await X.wait(1);
      },
      4: async () => {
        X.hero(-7, .5);
        await X.wait(.4);
        X.log('Fog node Z3 crashes.', 'warn');
        S.zones.Z3.alive = false; fx('fog:Z3', COL.hot);
        X.tag('fog:Z3', 'offline', COL.hot, 6);
        await X.wait(.6);
        X.log('Broker publishes Z3’s last-will: zone/3/status = offline → every zone.', 'state');
        await X.fan('state', [['broker','fog:Z1'],['broker','fog:Z2'],['broker','fog:Z4']], { from:'fog:Z3' });
        X.log('Car 7 sends a task in Z2.', 'task');
        X.role('Z2', 'anchor');
        await X.send('task', up('Z2'));
        await X.wait(.5);
        X.decide('Z2', { here:.49, n1:.44, n3:.72, cloud:.31 }, 'n3', 'Z3 is masked (offline); Z5 is not joined. Z4 has the best Q-value.');
        X.role('Z4', 'exec');
        await X.wait(.5);
        await X.send('task', ['fog:Z2','fog:Z4']);
        await X.exec('Z4', 1.3);
        await X.send('result', ['fog:Z4','broker', ...toCar(HERO)]);
        const ap = ackPath('Z2'); if (ap) await X.send('ack', ap);
        X.unrole('Z4', 'exec');
        await X.wait(.8);
        X.log('A 5th zone (Z5) comes online and connects to the broker.', 'state');
        S.zones.Z5.joined = true;
        await X.wait(1.2);
        await X.send('state', ['fog:Z5','broker']);
        X.log('Broker relays zone/5/status = online to its neighbours.', 'state');
        await X.fan('state', [['broker','fog:Z1'],['broker','fog:Z2'],['broker','fog:Z4']], { from:'fog:Z5' });
        X.tag('fog:Z5', 'online', COL.exec, 3);
        X.decide('Z2', { here:.49, n1:.44, n3:.66, n4:.70, cloud:.31 }, null, 'Z5 is now option N4 for Z2. Z3 stays masked until it reconnects.');
        X.log('Z2’s action set updates: Z5 available, Z3 masked. (Reset restores Z3.)', 'done');
        await X.wait(1);
      },
      5: async () => {
        X.hero(-23, .5);
        await X.wait(.3);
        X.log('Rush hour: heavy tasks (8–14 GFLOP) from many cars. TOF-Broker sends them straight to the cloud, skipping D3QN.', 'warn');
        for (let i = 0; i < 20; i++) {
          const cs = S.cars.filter(c => c.serv && c.id !== HERO);
          const c = cs[Math.floor(Math.random()*cs.length)];
          if (c) {
            const z = c.serv;
            if (i % 5 === 0) X.tag('fog:'+z, 'TOF → cloud', COL.task, 1.2);
            (async () => {
              if (await send('task', ['car:'+c.id,'ap:'+z,'fog:'+z,'broker','cloud'])) { await X.exec('cloud', 1.2); await send('result', ['cloud','broker', ...toCar(c.id)]); }
            })().catch(() => {});
          }
          await X.wait(.22);
          if (i === 10) X.log('WAN link saturates — latency climbs toward 200 ms.', 'warn');
        }
        await X.wait(.6);
        X.log('Car 7 sends a normal task in Z1.', 'task');
        X.role('Z1', 'anchor');
        await X.send('task', up('Z1'));
        await X.wait(.5);
        X.decide('Z1', { here:.71, n1:.58, cloud:.09 }, 'here', 'Cloud Q-value collapses: a ~'+Math.round(S.wanMs)+' ms WAN would miss the deadline.');
        X.log('D3QN keeps it local — the cloud is no longer the easy choice.', 'info');
        X.role('Z1', 'exec');
        await X.exec('Z1', 1.2);
        await X.send('result', ['fog:Z1','broker', ...toCar(HERO)]);
        const ap = ackPath('Z1'); if (ap) await X.send('ack', ap);
        await X.until(() => S.wanLoad <= 0);
        X.log('Queue drains; the WAN recovers.', 'done');
        await X.wait(1);
      },
    };
    try { await FL[n](); } catch (e) { if (e !== CANCEL) console.error(e); return; }
    await simWait(3);
    if (my.dead) return;
    for (const z of Object.values(S.zones)) z.roles.clear();
    S.flowActive = false; hero.v = hero.v0; call('onFlow', null);
  }

  // ---------- 3D view ----------
  function make3D() {
    const wrap = document.createElement('div'); wrap.style.cssText = 'position:absolute;inset:0;';
    root.appendChild(wrap);
    const renderer = new THREE.WebGLRenderer({ antialias:true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); renderer.setClearColor(COL.bg, 1);
    renderer.domElement.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none;cursor:grab;';
    wrap.appendChild(renderer.domElement);
    const layer = document.createElement('div'); layer.style.cssText = 'position:absolute;inset:0;pointer-events:none;overflow:hidden;';
    wrap.appendChild(layer);
    const scene = new THREE.Scene();
    const cam = new THREE.OrthographicCamera(-1,1,1,-1,0.1,600);
    const ctl = { az:Math.PI*0.22, el:0.62, zoom:1 }, target = new THREE.Vector3(0, 9, -7);
    function place() {
      const w = wrap.clientWidth || 1, h = wrap.clientHeight || 1, a = w/h, d = 160, I = S.insets;
      const aw = Math.max(200, w - I.left - I.right), ah = Math.max(200, h - I.top - I.bottom);
      cam.position.set(target.x + d*Math.cos(ctl.el)*Math.sin(ctl.az), target.y + d*Math.sin(ctl.el), target.z + d*Math.cos(ctl.el)*Math.cos(ctl.az));
      cam.lookAt(target);
      const hh = 27*Math.max(1, 1.6/(aw/ah))/ctl.zoom * (h/ah);
      const upp = 2*hh/h, dx = (I.left - I.right)/2*upp, dy = (I.top - I.bottom)/2*upp;
      cam.left = -hh*a - dx; cam.right = hh*a - dx; cam.top = hh + dy; cam.bottom = -hh + dy; cam.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    }
    scene.add(new THREE.HemisphereLight(0xc9d8e8, 0x0b0e13, 1.7));
    const dl = new THREE.DirectionalLight(0xffffff, 1.5); dl.position.set(25, 45, 30); scene.add(dl);
    const MS = (c, o = {}) => new THREE.MeshStandardMaterial({ color:c, roughness:.85, metalness:.05, ...o });
    const MB = (c, o = {}) => new THREE.MeshBasicMaterial({ color:c, ...o });
    const unit = new THREE.BoxGeometry(1,1,1);
    const box = (w,h,d,mat,x,y,z,parent=scene) => { const m = new THREE.Mesh(unit, mat); m.scale.set(w,h,d); m.position.set(x,y,z); parent.add(m); return m; };

    const g0 = new THREE.Mesh(new THREE.PlaneGeometry(110, 70), MS(COL.ground)); g0.rotation.x = -Math.PI/2; g0.position.set(0,0,-8); scene.add(g0);
    const roadM = MS(COL.road), dashM = MB(COL.dash);
    box(60,.06,3.4,roadM,0,.03,0); box(60,.06,3.4,roadM,0,.03,-16);
    box(3.4,.06,16,roadM,28,.03,-8); box(3.4,.06,16,roadM,-28,.03,-8);
    for (let x = -25; x <= 25; x += 3) { box(1.3,.07,.12,dashM,x,.04,0); box(1.3,.07,.12,dashM,x,.04,-16); }
    let seed = 11; const rnd = () => (seed = (seed*16807) % 2147483647) / 2147483647;
    const bM = [MS(0x18202a), MS(0x1c2530), MS(0x141b23)];
    const eqs = Object.values(S.zones).map(equip);
    for (let x = -40; x <= 40; x += 3.2) for (let z = -30; z <= 12; z += 3.2) {
      const onRoad = Math.abs(z) < 3.4 || Math.abs(z+16) < 3.4 || ((Math.abs(x-28) < 3.4 || Math.abs(x+28) < 3.4) && z < 2 && z > -18);
      const near = eqs.some(e => Math.hypot(e.x-x, e.z-z) < 3.6) || Math.hypot(x-BROKER.x, z-BROKER.z) < 5;
      if (onRoad || near || rnd() < .45) continue;
      const h = .4 + rnd()*rnd()*3.4, w = 1.8 + rnd()*.9;
      box(w, h, w, bM[Math.floor(rnd()*3)], x + (rnd()-.5)*.6, h/2, z + (rnd()-.5)*.6);
    }
    // tunnel
    box(6,1.9,4.6,MS(0x29313b),7.5,.95,0); box(.25,1.5,3.6,MB(0x050709),4.45,.75,0); box(.25,1.5,3.6,MB(0x050709),10.55,.75,0);

    const labels = [];
    const mkLabel = (html, at, opts = {}) => {
      const d = document.createElement('div');
      d.style.cssText = 'position:absolute;left:0;top:0;display:none;white-space:nowrap;font:500 11px '+MONO+';color:#c9d3de;background:rgba(11,14,19,.72);padding:2px 7px;border-radius:5px;' + (opts.css || '');
      d.innerHTML = html; layer.appendChild(d);
      const L = { el:d, at, vis:opts.vis, upd:opts.upd }; labels.push(L); return L;
    };

    // zones
    const ZV = {}, pickables = [];
    for (const z of Object.values(S.zones)) {
      const g = new THREE.Group(); g.position.set(z.x, 0, z.z); scene.add(g);
      const domeMat = MB(COL.dome, { transparent:true, opacity:.07, depthWrite:false, side:THREE.DoubleSide });
      const dome = new THREE.Mesh(new THREE.SphereGeometry(z.r, 48, 16, 0, Math.PI*2, 0, Math.PI/2), domeMat); dome.scale.y = .42; g.add(dome);
      const ringMat = MB(COL.dome, { transparent:true, opacity:.6, depthWrite:false });
      const ring = new THREE.Mesh(new THREE.RingGeometry(z.r-.15, z.r, 96), ringMat); ring.rotation.x = -Math.PI/2; ring.position.y = .09; g.add(ring);
      const discMat = MB(COL.dome, { transparent:true, opacity:.035, depthWrite:false });
      const disc = new THREE.Mesh(new THREE.CircleGeometry(z.r, 64), discMat); disc.rotation.x = -Math.PI/2; disc.position.y = .08; g.add(disc);
      const e = equip(z); const eg = new THREE.Group(); eg.position.set(e.x, 0, e.z); scene.add(eg);
      box(3.4,.14,1.9,MS(0x1d242d),0,.07,0,eg);
      const poleM = MS(0x8592a0);
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(.1,.16,5.6,8), poleM); pole.position.set(-.9,2.8,0); eg.add(pole);
      box(1,.08,.08,poleM,-.9,5.2,0,eg); box(.8,.08,.08,poleM,-.9,4.7,0,eg);
      const headM = MB(0xdfe8f2); const head = new THREE.Mesh(new THREE.SphereGeometry(.32,16,12), headM); head.position.set(-.9,5.9,0); eg.add(head);
      const cabM = MS(0x26303c); const cab = box(1.3,1.8,1.0,cabM,.9,.9,0,eg);
      const capM = MB(0x8a96a4); box(1.42,.1,1.12,capM,.9,1.85,0,eg);
      const leds = [0,1,2,3].map(i => box(1.0,.17,.04,MB(COL.led),.9,.4+i*.36,.52,eg));
      const ledsX = [0,1,2,3].map(i => box(.04,.17,.8,MB(COL.led),1.57,.4+i*.36,0,eg));
      [cab, pole, head].forEach(m => { m.userData.zone = z.id; pickables.push(m); });
      ZV[z.id] = { g, eg, domeMat, ringMat, discMat, leds, ledsX, capM, headM, cabM };
      mkLabel('', () => new THREE.Vector3(e.x-.9, 7.1, e.z), { css:'background:transparent;padding:0;', upd: el => {
        const html = '<span style="font:600 13px '+SANS+';color:#eef3f8">'+z.id+'</span> <span style="color:#7d8a99">'+(!z.joined ? 'can join' : !z.alive ? 'offline' : 'fog zone')+'</span>';
        if (el.__h !== html) { el.innerHTML = html; el.__h = html; }
        el.style.opacity = z.joined ? (z.alive ? 1 : .55) : .35;
      } });
    }
    // broker
    const bg = new THREE.Group(); bg.position.set(BROKER.x, 0, BROKER.z); scene.add(bg);
    const bcM = MS(COL.broker, { emissive:0x15191e });
    const c0 = new THREE.Mesh(new THREE.CylinderGeometry(2,2.2,.3,24), MS(0x1f262f)); c0.position.y = .15; bg.add(c0);
    for (let k = 0; k < 3; k++) { const a = k*Math.PI*2/3; const c = new THREE.Mesh(new THREE.CylinderGeometry(.48,.48,6,16), bcM); c.position.set(Math.cos(a)*.8, 3.2, Math.sin(a)*.8); bg.add(c); }
    const ct = new THREE.Mesh(new THREE.CylinderGeometry(1.7,1.7,.16,24), MS(0x6d7682)); ct.position.y = 6.3; bg.add(ct);
    const bb = new THREE.Mesh(new THREE.SphereGeometry(.26,16,12), MB(0xdfe6ee)); bb.position.y = 6.8; bg.add(bb);
    mkLabel('<span style="font:600 12px '+SANS+';color:#eef3f8">MQTT broker</span> <span style="color:#8b97a5">EMQX cluster · metro edge</span>', () => new THREE.Vector3(BROKER.x, 8.2, BROKER.z));

    function pos3(id) {
      const [k, v] = id.split(':');
      if (k === 'car') { const p = carPos(CAR[v]); return new THREE.Vector3(p.x, .8, p.z); }
      if (k === 'ap') { const e = equip(S.zones[v]); return new THREE.Vector3(e.x-.9, 5.9, e.z); }
      if (k === 'fog') { const e = equip(S.zones[v]); return new THREE.Vector3(e.x+.9, 2.0, e.z); }
      if (id === 'broker') return new THREE.Vector3(BROKER.x, 6.8, BROKER.z);
      return new THREE.Vector3(BROKER.x, CLOUD_Y-.4, BROKER.z);
    }
    function seg3(a, b) {
      const A = pos3(a), B = pos3(b), ka = kind(a), kb = kind(b);
      if (ka==='car'||kb==='car'||ka==='ap'||kb==='ap'||isWan(a,b)) return [A, B];
      const M = A.clone().add(B).multiplyScalar(.5); M.y = Math.max(A.y, B.y) + 1.5 + A.distanceTo(B)*.1;
      const pts = []; for (let i = 0; i <= 16; i++) { const t = i/16, u = 1-t; pts.push(new THREE.Vector3(u*u*A.x+2*u*t*M.x+t*t*B.x, u*u*A.y+2*u*t*M.y+t*t*B.y, u*u*A.z+2*u*t*M.z+t*t*B.z)); }
      return pts;
    }
    const links = [];
    for (const z of Object.values(S.zones)) {
      const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(seg3('fog:'+z.id, 'broker')), new THREE.LineBasicMaterial({ color:COL.link, transparent:true, opacity:.6 }));
      scene.add(l); links.push({ l, zs:[z.id], base:.6 });
    }
    for (const [a, b] of PEERS) {
      const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(seg3('fog:'+a, 'fog:'+b)), new THREE.LineDashedMaterial({ color:COL.link, dashSize:.5, gapSize:.35, transparent:true, opacity:.4 }));
      l.computeLineDistances(); scene.add(l); links.push({ l, zs:[a,b], base:.4 });
    }
    { const pts = seg3('fog:Z2','broker'); mkLabel('backhaul · 1–5 ms', () => pts[8].clone().add(new THREE.Vector3(0,.6,0)), { css:'color:#8b97a5;' }); }
    // WAN + cloud
    const wA = pos3('broker'), wB = pos3('cloud'), wl = wB.y - wA.y;
    const wanMat = MB(COL.wan);
    const wan = new THREE.Mesh(new THREE.CylinderGeometry(.06,.06,wl,8), wanMat); wan.position.set(BROKER.x, (wA.y+wB.y)/2, BROKER.z); scene.add(wan);
    const wgM = MB(COL.hot, { transparent:true, opacity:0, depthWrite:false });
    const wg = new THREE.Mesh(new THREE.CylinderGeometry(.4,.4,wl,12,1,true), wgM); wg.position.copy(wan.position); scene.add(wg);
    mkLabel('', () => new THREE.Vector3(BROKER.x, (wA.y+wB.y)/2, BROKER.z), { css:'transform-origin:left;', upd: el => {
      const hot = Math.min(1, Math.max(0, S.wanLoad)/9);
      el.innerHTML = 'WAN · <b style="color:'+(hot > .5 ? '#ff6b6b' : '#9fd8e8')+'">'+Math.round(S.wanMs)+' ms</b>'; el.__dx = 14;
    } });
    const cg = new THREE.Group(); cg.position.set(BROKER.x, CLOUD_Y, BROKER.z); scene.add(cg);
    box(15,.7,8,MS(0x18222e),0,0,0,cg);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(15,.7,8)), new THREE.LineBasicMaterial({ color:0x35506a })); cg.add(edges);
    const cloudLeds = [];
    for (let j = 0; j < 3; j++) for (let i = 0; i < 8; i++) cloudLeds.push(box(1.1,.3,1.1,MB(COL.led),-5.6+i*1.6,.5,-1.6+j*1.6,cg));
    const puffM = MB(0xcfe0f0, { transparent:true, opacity:.045, depthWrite:false });
    [[-5,1.5,0,4.5],[1,2.5,-1,5.5],[6,1.4,.5,4],[-1,.8,2,4.5]].forEach(([x,y,z,r]) => { const m = new THREE.Mesh(new THREE.SphereGeometry(r,24,16), puffM); m.position.set(x,y,z); cg.add(m); });
    mkLabel('<span style="font:600 13px '+SANS+';color:#eef3f8">Cloud</span> <span style="color:#8b97a5">data centre · queue + 24 slots</span>', () => new THREE.Vector3(BROKER.x, CLOUD_Y+4.2, BROKER.z));
    mkLabel('tunnel · no coverage', () => new THREE.Vector3(7.5, 2.4, 0), { css:'color:#8b97a5;' });
    // cars
    const carM = MS(COL.car, { emissive:0x3a2a00 }), cabCM = MS(0x1d222a);
    const CV = {};
    for (const c of S.cars) {
      const g = new THREE.Group(); scene.add(g);
      box(1.5,.5,.8,carM,0,.4,0,g); box(.8,.36,.7,cabCM,-.1,.8,0,g);
      if (c.id === HERO) {
        const hm = MB(COL.car, { transparent:true, opacity:.7, depthWrite:false });
        const h = new THREE.Mesh(new THREE.RingGeometry(1.15,1.4,40), hm); h.rotation.x = -Math.PI/2; h.position.y = .08; g.add(h); g.userData.halo = h;
      }
      CV[c.id] = g;
    }
    mkLabel('<span style="color:#ffd23f;font-weight:600">car 7</span>', () => pos3('car:'+HERO).add(new THREE.Vector3(0,1.3,0)), { css:'border:1px solid rgba(255,210,63,.35);' });
    const radioArr = new Float32Array(S.cars.length*6);
    const radioGeo = new THREE.BufferGeometry(); radioGeo.setAttribute('position', new THREE.BufferAttribute(radioArr, 3));
    const radioM = new THREE.LineBasicMaterial({ color:0xd8e2ee, transparent:true, opacity:.2 });
    scene.add(new THREE.LineSegments(radioGeo, radioM));
    const heroArr = new Float32Array(6); const heroGeo = new THREE.BufferGeometry(); heroGeo.setAttribute('position', new THREE.BufferAttribute(heroArr, 3));
    const heroLine = new THREE.Line(heroGeo, new THREE.LineDashedMaterial({ color:COL.car, transparent:true, opacity:.85, dashSize:.4, gapSize:.25 })); scene.add(heroLine);
    mkLabel('radio', () => { const a = pos3('car:'+HERO), b = hero.serv ? pos3('ap:'+hero.serv) : a; return a.lerp(b, .5); }, { vis:() => !!hero.serv, css:'color:#ffd23f;font-size:10px;' });

    const pGeo = new THREE.SphereGeometry(.34, 14, 10), pMats = {}, gMats = {};
    for (const k in PCOL) { pMats[k] = MB(PCOL[k]); gMats[k] = MB(PCOL[k], { transparent:true, opacity:.25, depthWrite:false }); }
    const fMat = MB(COL.state, { transparent:true, opacity:.45 });
    const pm = new Map();
    const fxGeo = new THREE.RingGeometry(.4,.6,28), fxm = new Map();
    const C1 = new THREE.Color(), C2 = new THREE.Color();
    function zoneLook(z) {
      const serv = S.flowActive && hero.serv === z.id, anchor = z.roles.has('anchor');
      if (!z.alive) return { fill:COL.dead, ring:COL.dead, a:.05 };
      const fill = anchor ? COL.anchor : serv ? COL.serving : COL.dome;
      return { fill, ring:anchor && serv ? COL.serving : fill, a:(anchor || serv) ? .15 : .06 };
    }
    const v = new THREE.Vector3();
    function screen(id) { const w = wrap.clientWidth, h = wrap.clientHeight; v.copy(pos3(id)).project(cam); return { x:(v.x+1)/2*w, y:(1-v.y)/2*h }; }

    function render(now) {
      for (const c of S.cars) {
        const p = carPos(c), g = CV[c.id]; g.position.set(p.x, 0, p.z);
        g.rotation.y = Math.atan2(-p.dz*c.dir, p.dx*c.dir);
        if (g.userData.halo) { const s = 1 + .12*Math.sin(now*.005); g.userData.halo.scale.set(s,s,s); }
      }
      let k = 0;
      for (const c of S.cars) {
        let a, b;
        if (S.radio && c.serv && c !== hero) { a = pos3('car:'+c.id); b = pos3('ap:'+c.serv); } else { a = b = new THREE.Vector3(0,-5,0); }
        radioArr.set([a.x,a.y,a.z,b.x,b.y,b.z], k); k += 6;
      }
      radioGeo.attributes.position.needsUpdate = true;
      heroLine.visible = !!hero.serv;
      if (hero.serv) { const a = pos3('car:'+HERO), b = pos3('ap:'+hero.serv); heroArr.set([a.x,a.y,a.z,b.x,b.y,b.z]); heroGeo.attributes.position.needsUpdate = true; heroLine.computeLineDistances(); }
      for (const z of Object.values(S.zones)) {
        const V = ZV[z.id], f = z.fade, L = zoneLook(z);
        V.g.visible = V.eg.visible = f > .01;
        V.eg.scale.set(1, Math.max(.01, f), 1);
        V.domeMat.color.setHex(L.fill); V.domeMat.opacity = L.a*f;
        V.ringMat.color.setHex(L.ring); V.ringMat.opacity = (z.alive ? .7 : .3)*f;
        V.discMat.color.setHex(L.fill); V.discMat.opacity = (L.a*.5)*f;
        const lit = i => z.alive && z.slots[i] > 0;
        V.leds.forEach((m, i) => m.material.color.setHex(lit(i) ? COL.exec : z.alive ? COL.led : 0x111418));
        V.ledsX.forEach((m, i) => m.material.color.setHex(lit(i) ? COL.exec : z.alive ? COL.led : 0x111418));
        V.capM.color.setHex(!z.alive ? COL.dead : z.roles.has('exec') ? COL.exec : z.roles.has('anchor') ? COL.anchor : 0x8a96a4);
        V.headM.color.setHex(z.alive ? (S.flowActive && hero.serv === z.id ? COL.serving : 0xdfe8f2) : COL.dead);
        V.cabM.emissive.setHex(S.sel === z.id ? 0x34506a : 0x000000);
      }
      for (const L of links) {
        const zs = L.zs.map(id => S.zones[id]); const f = Math.min(...zs.map(z => z.fade));
        L.l.visible = f > .02; L.l.material.opacity = (zs.every(z => z.alive) ? L.base : .08)*f;
      }
      const hot = Math.min(1, Math.max(0, S.wanLoad)/9);
      wanMat.color.copy(C1.setHex(COL.wan).lerp(C2.setHex(COL.hot), hot)); wgM.opacity = hot*.3;
      wan.scale.set(1 + hot*1.5, 1, 1 + hot*1.5);
      cloudLeds.forEach((m, i) => m.material.color.setHex(S.cloudSlots[i] > 0 ? COL.exec : COL.led));
      const live = new Set(S.packets);
      for (const [p, m] of pm) if (!live.has(p)) { scene.remove(m); pm.delete(p); }
      for (const p of S.packets) {
        let m = pm.get(p);
        if (!m) {
          m = new THREE.Mesh(pGeo, p.faint ? fMat : pMats[p.type]);
          if (!p.faint) { const gl = new THREE.Mesh(pGeo, gMats[p.type]); gl.scale.setScalar(2.3); m.add(gl); }
          scene.add(m); pm.set(p, m);
        }
        const [A, B, t] = along(seg3(p.ids[p.seg], p.ids[p.seg+1]), p.t, (a, b) => a.distanceTo(b));
        m.position.copy(A).lerp(B, t); m.scale.setScalar(p.size*(p.faint ? .7 : 1));
      }
      const fl = new Set(S.fx);
      for (const [f, m] of fxm) if (!fl.has(f)) { scene.remove(m); fxm.delete(f); }
      for (const f of S.fx) {
        let m = fxm.get(f);
        if (!m) { m = new THREE.Mesh(fxGeo, MB(f.color, { transparent:true, depthWrite:false, side:THREE.DoubleSide })); scene.add(m); fxm.set(f, m); m.position.copy(pos3(f.id)); }
        m.lookAt(cam.position); m.scale.setScalar(1 + f.t*5); m.material.opacity = 1 - f.t/.9;
      }
      renderer.render(scene, cam);
      const w = wrap.clientWidth, h = wrap.clientHeight;
      for (const L of labels) {
        if (L.upd) L.upd(L.el);
        const vis = L.vis ? L.vis() : true;
        if (!vis) { L.el.style.display = 'none'; continue; }
        v.copy(L.at()).project(cam);
        L.el.style.display = '';
        const dx = L.el.__dx;
        L.el.style.transform = 'translate(' + ((v.x+1)/2*w + (dx || 0)) + 'px,' + ((1-v.y)/2*h) + 'px) translate(' + (dx ? '0' : '-50%') + ',-100%)';
      }
    }
    // interaction
    const el = renderer.domElement, ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
    function pick(e) {
      const r = el.getBoundingClientRect();
      ndc.set(((e.clientX-r.left)/r.width)*2-1, -((e.clientY-r.top)/r.height)*2+1);
      ray.setFromCamera(ndc, cam);
      const hits = ray.intersectObjects(pickables.filter(m => { let p = m.parent; return p.visible && S.zones[m.userData.zone].fade > .5; }), false);
      return hits.length ? hits[0].object.userData.zone : null;
    }
    let drag = null;
    el.addEventListener('pointerdown', e => { drag = { x:e.clientX, y:e.clientY, moved:false }; el.setPointerCapture(e.pointerId); });
    el.addEventListener('pointermove', e => {
      if (drag) {
        const dx = e.clientX-drag.x, dy = e.clientY-drag.y;
        if (!drag.moved && Math.abs(dx)+Math.abs(dy) > 4) drag.moved = true;
        if (drag.moved) { ctl.az -= dx*.006; ctl.el = Math.max(.2, Math.min(1.35, ctl.el + dy*.004)); drag.x = e.clientX; drag.y = e.clientY; place(); el.style.cursor = 'grabbing'; }
      } else el.style.cursor = pick(e) ? 'pointer' : 'grab';
    });
    el.addEventListener('pointerup', e => { if (drag && !drag.moved) { const z = pick(e); S.sel = z; call('onSelect', z); } drag = null; el.style.cursor = 'grab'; });
    el.addEventListener('wheel', e => { e.preventDefault(); ctl.zoom = Math.max(.5, Math.min(4, ctl.zoom*Math.exp(-e.deltaY*.0012))); place(); }, { passive:false });
    place();
    return { render, screen, place, show:on => wrap.style.display = on ? '' : 'none', dispose:() => renderer.dispose() };
  }

  // ---------- poster view ----------
  function makePoster() {
    const NS = 'http://www.w3.org/2000/svg';
    const wrap = document.createElement('div'); wrap.style.cssText = 'position:absolute;inset:0;display:none;background:#0b0e13;';
    root.appendChild(wrap);
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 1300 1000'); svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.setAttribute('font-family', MONO);
    svg.style.cssText = 'position:absolute;top:64px;bottom:44px;left:0;right:0;width:100%;height:calc(100% - 108px);';
    wrap.appendChild(svg);
    const E = (t, a, p = svg) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
    const T = (x, y, txt, a = {}, p = svg) => { const e = E('text', { x, y, ...a }, p); e.textContent = txt; return e; };
    const ZX = { Z1:190, Z2:420, Z3:650, Z4:880, Z5:1110 };
    const RY = { A:770, B:900 };
    const mapX = wx => 90 + (wx+30)/60*1120;
    const BUS = 304, TOP = 380, PEER = 362;
    [[20,250,'CLOUD','one data centre · far away'],[20,0,'',''],[326,666,'FOG','road-side zones · 1–5 ms backhaul between zones and to the broker'],[682,982,'IoT','cars talk only by radio to the zone they are in']].forEach(([y0,y1,t,s]) => {
      if (!t) return;
      E('rect', { x:20, y:y0, width:1260, height:y1-y0, rx:16, fill:'#0e131a', stroke:'#1a212b' });
      T(40, y0+32, t, { fill:'#eef3f8', 'font-size':18, 'font-weight':600, 'letter-spacing':3, 'font-family':SANS });
      T(40 + t.length*16 + 18, y0+31, s, { fill:'#6f7c8b', 'font-size':14 });
    });
    // cloud
    E('rect', { x:410, y:46, width:480, height:174, rx:14, fill:'#141c26', stroke:'#35506a', 'stroke-width':2 });
    T(432, 82, 'Cloud', { fill:'#eef3f8', 'font-size':24, 'font-weight':600, 'font-family':SANS });
    T(868, 81, 'queue + 24 execution slots', { fill:'#7d8a99', 'font-size':14, 'text-anchor':'end' });
    const cSlots = [];
    for (let j = 0; j < 2; j++) for (let i = 0; i < 12; i++) cSlots.push(E('rect', { x:432+i*36.5, y:124+j*34, width:28, height:22, rx:4, fill:H6(COL.led) }));
    const wanLine = E('line', { x1:650, y1:220, x2:650, y2:290, stroke:H6(COL.wan), 'stroke-width':3 });
    const wanTxt = T(664, 262, 'WAN · 50 ms', { fill:'#9fd8e8', 'font-size':16 });
    // bus
    E('rect', { x:60, y:290, width:1180, height:28, rx:14, fill:'#262c34', stroke:'#4b535d', 'stroke-width':1.5 });
    T(70, 282, 'MQTT broker · EMQX cluster (metro edge)', { fill:'#c9d1da', 'font-size':16, 'font-weight':500 });
    T(1230, 282, 'clients: zones + cloud · cars are not', { fill:'#6f7c8b', 'font-size':14, 'text-anchor':'end' });
    E('line', { x1:190, y1:PEER, x2:1110, y2:PEER, stroke:H6(COL.link), 'stroke-width':1.5, 'stroke-dasharray':'6 6', opacity:.6 });
    // roads
    for (const r of ['A','B']) {
      E('rect', { x:90, y:RY[r]-20, width:1120, height:40, rx:6, fill:'#171d25' });
      E('line', { x1:100, y1:RY[r], x2:1200, y2:RY[r], stroke:H6(COL.dash), 'stroke-width':1.5, 'stroke-dasharray':'14 12' });
      T(1210, RY[r]+48, r==='A' ? 'north road' : 'south road', { fill:'#56616f', 'font-size':13, 'text-anchor':'end' });
    }
    E('rect', { x:mapX(4.5), y:RY.A-24, width:mapX(10.5)-mapX(4.5), height:48, rx:6, fill:'#0a0d11', stroke:'#3a4552', 'stroke-dasharray':'4 4' });
    T((mapX(4.5)+mapX(10.5))/2, RY.A+48, 'tunnel · no coverage', { fill:'#8b97a5', 'font-size':13, 'text-anchor':'middle' });
    const radioG = E('g', {}), linkG = E('g', {});
    const PV = {};
    for (const z of Object.values(S.zones)) {
      const cx = ZX[z.id], x0 = cx-100, y0 = TOP, ry = z.z === 0 ? RY.A : RY.B;
      const up = E('line', { x1:cx, y1:318, x2:cx, y2:TOP, stroke:H6(COL.link), 'stroke-width':2 }, linkG);
      const span = E('rect', { x:mapX(z.x-z.r), y:ry-30, width:mapX(z.x+z.r)-mapX(z.x-z.r), height:60, rx:10, fill:H6(COL.dome), 'fill-opacity':.1, stroke:H6(COL.dome), 'stroke-opacity':.6, 'stroke-width':1.5 });
      const spanT = T(mapX(z.x-z.r)+8, ry-38, z.id, { fill:'#c9d3de', 'font-size':15, 'font-weight':600 });
      const g = E('g', { style:'cursor:pointer' });
      g.addEventListener('click', () => { S.sel = z.id; call('onSelect', z.id); });
      const card = E('rect', { x:x0, y:y0, width:200, height:240, rx:14, fill:'#121821', stroke:'#2a3440', 'stroke-width':2 }, g);
      T(x0+16, y0+34, z.id, { fill:'#eef3f8', 'font-size':26, 'font-weight':600, 'font-family':SANS }, g);
      const status = T(x0+186, y0+32, 'online', { fill:'#7d8a99', 'font-size':14, 'text-anchor':'end' }, g);
      const chips = { anchor:T(x0+16, y0+58, 'ANCHOR', { fill:H6(COL.anchor), 'font-size':12, 'font-weight':600, style:'display:none' }, g), serving:T(x0+80, y0+58, 'SERVING', { fill:H6(COL.serving), 'font-size':12, 'font-weight':600, style:'display:none' }, g), exec:T(x0+148, y0+58, 'EXEC', { fill:H6(COL.exec), 'font-size':12, 'font-weight':600, style:'display:none' }, g) };
      let qT;
      ['TOF-Broker','D3QN agent','Priority queue'].forEach((t, i) => {
        E('rect', { x:x0+14, y:y0+70+i*34, width:172, height:28, rx:6, fill:'#19212c', stroke:'#2a3440' }, g);
        T(x0+24, y0+89+i*34, t, { fill:'#c9d3de', 'font-size':15 }, g);
        if (i === 2) qT = T(x0+176, y0+89+i*34, '0', { fill:'#7d8a99', 'font-size':14, 'text-anchor':'end' }, g);
      });
      const slots = [0,1,2,3].map(i => E('rect', { x:x0+14+i*44, y:y0+178, width:36, height:22, rx:4, fill:H6(COL.led) }, g));
      T(x0+16, y0+226, 'mobility · state store', { fill:'#6f7c8b', 'font-size':13 }, g);
      const ant = E('line', { x1:cx, y1:620, x2:cx, y2:640, stroke:'#8592a0', 'stroke-width':2 });
      const apC = E('circle', { cx, cy:644, r:5, fill:'#dfe8f2' });
      PV[z.id] = { g, card, status, chips, slots, qT, up, span, spanT, ant, apC };
    }
    const carEls = {};
    for (const c of S.cars) {
      const r = E('rect', { width:30, height:16, rx:4, fill:H6(COL.car), stroke:c.id === HERO ? '#ffffff' : 'none', 'stroke-width':2 });
      carEls[c.id] = { r, line:E('line', { stroke:'#d8e2ee', 'stroke-opacity':.22, 'stroke-width':1.2 }, radioG) };
    }
    const heroT = T(0, 0, 'car 7', { fill:H6(COL.car), 'font-size':14, 'font-weight':600, 'text-anchor':'middle' });
    carEls[HERO].line.setAttribute('stroke', H6(COL.car)); carEls[HERO].line.setAttribute('stroke-opacity', .8); carEls[HERO].line.setAttribute('stroke-dasharray', '5 4');
    const pktG = E('g', {}), fxG = E('g', {});

    function pos2(id) {
      const [k, v] = id.split(':');
      if (k === 'car') { const c = CAR[v], p = carPos(c); return { x:mapX(p.x), y:(p.z > -8 ? RY.A : RY.B) + (c.dir > 0 ? -8 : 8) }; }
      if (k === 'ap') return { x:ZX[v], y:644 };
      if (k === 'fog') return { x:ZX[v], y:395 };
      if (id === 'broker') return { x:650, y:BUS };
      return { x:650, y:150 };
    }
    const xOf = id => !id ? 650 : id === 'broker' ? 650 : pos2(id).x;
    function seg2(a, b, prev) {
      const ka = kind(a), kb = kind(b);
      if (ka==='fog' && b==='broker') { const x = ZX[a.split(':')[1]]; return [pos2(a), { x, y:TOP }, { x, y:BUS }]; }
      if (a==='broker' && kb==='fog') { const x = ZX[b.split(':')[1]], px = xOf(prev); return [{ x:px, y:BUS }, { x, y:BUS }, { x, y:TOP }, pos2(b)]; }
      if (a==='broker' && b==='cloud') { const px = xOf(prev); return [{ x:px, y:BUS }, { x:650, y:BUS }, { x:650, y:220 }, pos2(b)]; }
      if (a==='cloud' && b==='broker') return [pos2(a), { x:650, y:220 }, { x:650, y:BUS }];
      if (ka==='fog' && kb==='fog') { const xa = ZX[a.split(':')[1]], xb = ZX[b.split(':')[1]]; return [pos2(a), { x:xa, y:TOP }, { x:xa, y:PEER }, { x:xb, y:PEER }, { x:xb, y:TOP }, pos2(b)]; }
      return [pos2(a), pos2(b)];
    }
    const pm = new Map(), fxm = new Map();
    const C1 = new THREE.Color(), C2 = new THREE.Color();
    function render() {
      for (const c of S.cars) {
        const p = pos2('car:'+c.id), e = carEls[c.id];
        e.r.setAttribute('x', p.x-15); e.r.setAttribute('y', p.y-8);
        if (c.serv && (S.radio || c.id === HERO)) { const a = pos2('ap:'+c.serv); e.line.setAttribute('x1', p.x); e.line.setAttribute('y1', p.y-8); e.line.setAttribute('x2', a.x); e.line.setAttribute('y2', a.y); e.line.style.display = ''; }
        else e.line.style.display = 'none';
        if (c.id === HERO) { heroT.setAttribute('x', p.x); heroT.setAttribute('y', p.y-16); }
      }
      for (const z of Object.values(S.zones)) {
        const V = PV[z.id], f = z.fade, serv = S.flowActive && hero.serv === z.id, anchor = z.roles.has('anchor');
        const col = !z.alive ? COL.dead : anchor ? COL.anchor : serv ? COL.serving : null;
        V.card.setAttribute('stroke', S.sel === z.id ? '#ffffff' : col ? H6(col) : '#2a3440');
        V.card.setAttribute('stroke-dasharray', z.joined ? 'none' : '8 6');
        V.card.setAttribute('fill', z.alive ? '#121821' : '#15181c');
        V.g.setAttribute('opacity', (z.joined ? 1 : .35) * (z.alive ? 1 : .5) * (.35 + .65*f));
        V.status.textContent = !z.joined ? 'can join later' : !z.alive ? 'offline' : 'online';
        V.status.setAttribute('fill', !z.alive ? '#ff6b6b' : '#7d8a99');
        V.chips.anchor.style.display = anchor ? '' : 'none';
        V.chips.serving.style.display = serv ? '' : 'none';
        V.chips.exec.style.display = z.roles.has('exec') ? '' : 'none';
        V.slots.forEach((s, i) => s.setAttribute('fill', z.alive && z.slots[i] > 0 ? H6(COL.exec) : z.alive ? H6(COL.led) : '#111418'));
        V.qT.textContent = z.queue ? z.queue + ' waiting' : '0';
        V.up.setAttribute('opacity', (z.alive ? 1 : .2) * (z.joined ? 1 : .3));
        V.up.setAttribute('stroke-dasharray', z.joined ? 'none' : '4 6');
        const sc = col || COL.dome;
        V.span.setAttribute('fill', H6(sc)); V.span.setAttribute('stroke', H6(sc));
        V.span.setAttribute('fill-opacity', (col && z.alive ? .2 : .08) * f); V.span.setAttribute('stroke-opacity', .7*f);
        V.span.setAttribute('stroke-dasharray', z.joined ? 'none' : '6 6');
        V.spanT.setAttribute('opacity', .3 + .7*f);
        V.apC.setAttribute('fill', z.alive ? (serv ? H6(COL.serving) : '#dfe8f2') : H6(COL.dead));
        V.ant.setAttribute('opacity', .3 + .7*f); V.apC.setAttribute('opacity', .3 + .7*f);
      }
      const hot = Math.min(1, Math.max(0, S.wanLoad)/9);
      wanLine.setAttribute('stroke', '#' + C1.setHex(COL.wan).lerp(C2.setHex(COL.hot), hot).getHexString());
      wanLine.setAttribute('stroke-width', 3 + hot*6);
      wanTxt.textContent = 'WAN · ' + Math.round(S.wanMs) + ' ms'; wanTxt.setAttribute('fill', hot > .5 ? '#ff6b6b' : '#9fd8e8');
      cSlots.forEach((s, i) => s.setAttribute('fill', S.cloudSlots[i] > 0 ? H6(COL.exec) : H6(COL.led)));
      const live = new Set(S.packets);
      for (const [p, el] of pm) if (!live.has(p)) { el.remove(); pm.delete(p); }
      for (const p of S.packets) {
        let el = pm.get(p);
        if (!el) {
          el = E('g', {}, pktG); const c = H6(PCOL[p.type]);
          if (!p.faint) E('circle', { r:18*p.size, fill:c, opacity:.22 }, el);
          E('circle', { r:(p.faint ? 5 : 9)*p.size, fill:c, opacity:p.faint ? .5 : 1 }, el);
          pm.set(p, el);
        }
        const prev = p.seg > 0 ? p.ids[p.seg-1] : p.from;
        const [A, B, t] = along(seg2(p.ids[p.seg], p.ids[p.seg+1], prev), p.t, (a, b) => Math.hypot(a.x-b.x, a.y-b.y));
        el.setAttribute('transform', 'translate(' + (A.x + (B.x-A.x)*t) + ',' + (A.y + (B.y-A.y)*t) + ')');
      }
      const fl = new Set(S.fx);
      for (const [f, el] of fxm) if (!fl.has(f)) { el.remove(); fxm.delete(f); }
      for (const f of S.fx) {
        let el = fxm.get(f);
        if (!el) { const p = pos2(f.id); el = E('circle', { cx:p.x, cy:p.y, fill:'none', stroke:H6(f.color), 'stroke-width':3 }, fxG); fxm.set(f, el); }
        el.setAttribute('r', 8 + f.t*60); el.setAttribute('opacity', 1 - f.t/.9);
      }
    }
    function screen(id) {
      const p = pos2(id), m = svg.getScreenCTM(), r = root.getBoundingClientRect();
      if (!m) return { x:0, y:0 };
      return { x:m.a*p.x + m.e - r.left, y:m.d*p.y + m.f - r.top - (kind(id) === 'fog' ? 6 : 0) };
    }
    function layout() {
      const I = S.insets;
      svg.style.left = I.left + 'px'; svg.style.top = I.top + 'px'; svg.style.right = 'auto'; svg.style.bottom = 'auto';
      svg.style.width = 'calc(100% - ' + (I.left + I.right) + 'px)'; svg.style.height = 'calc(100% - ' + (I.top + I.bottom) + 'px)';
    }
    return { render, screen, place:layout, show:on => { if (on) { layout(); render(); } wrap.style.display = on ? '' : 'none'; } };
  }

  const v3 = make3D(), vp = makePoster();
  let view = v3;
  const tagLayer = document.createElement('div'); tagLayer.style.cssText = 'position:absolute;inset:0;pointer-events:none;overflow:hidden;';
  root.appendChild(tagLayer);
  function renderTags() {
    for (const t of S.tags) {
      if (!t.el) {
        t.el = document.createElement('div');
        t.el.style.cssText = 'position:absolute;left:0;top:0;visibility:hidden;white-space:nowrap;font:600 11px ' + MONO + ';padding:3px 8px;border-radius:6px;background:rgba(11,14,19,.9);border:1px solid ' + t.color + ';color:' + t.color + ';';
        t.el.textContent = t.text; tagLayer.appendChild(t.el);
      }
      const p = view.screen(t.id);
      t.el.style.opacity = Math.min(1, t.ttl*2);
      t.el.style.transform = 'translate(' + p.x + 'px,' + p.y + 'px) translate(-50%,-150%)';
      t.el.style.visibility = 'visible';
    }
  }
  const ro = new ResizeObserver(() => { v3.place(); vp.place(); }); ro.observe(root);
  let last = performance.now(), raf, tickT = 0, alive = true;
  function frame(now) {
    if (!alive) return;
    const dt = Math.min(.05, (now - last)/1000); last = now;
    step(dt); view.render(now); renderTags();
    tickT -= dt;
    if (tickT <= 0) {
      tickT = .25;
      const zones = {};
      for (const z of Object.values(S.zones)) zones[z.id] = { id:z.id, alive:z.alive, joined:z.joined, slots:z.slots.map(v => v > 0), queue:z.queue, held:z.held, roles:[...z.roles].concat(S.flowActive && hero.serv === z.id ? ['serving'] : []), cars:S.cars.filter(c => c.serv === z.id).length, neigh:NEIGH[z.id].map((n, i) => ({ slot:'N'+(i+1), id:n || '—', state:!n ? 'none' : !S.zones[n].joined ? 'not joined' : !S.zones[n].alive ? 'offline' : 'online' })) };
      const hot = Math.min(1, Math.max(0, S.wanLoad)/9);
      call('onTick', { zones, wanMs:Math.round(S.wanMs), wanHot:hot });
    }
    raf = requestAnimationFrame(frame);
  }
  raf = requestAnimationFrame(frame);
  return {
    play: n => runFlow(n),
    reset: () => { reset(); call('onClear'); },
    setView: k => { view = k === 'poster' ? vp : v3; v3.show(view === v3); vp.show(view === vp); S.tags.forEach(t => t.el && (t.el.style.opacity = 0)); },
    set: o => Object.assign(S, o),
    setInsets: i => { S.insets = { ...S.insets, ...i }; v3.place(); vp.place(); },
    select: z => { S.sel = z; },
    destroy: () => { alive = false; cancelAnimationFrame(raf); ro.disconnect(); reset(); v3.dispose(); root.innerHTML = ''; },
  };
}
