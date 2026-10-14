# PCNME — Data Flow

> Only what is decided. Anything not yet confirmed is marked **[OPEN]**.

## Rules

- **One task = one atomic job.** It runs entirely on one node (fog node CPU/GPU, or the cloud). Tasks are never split across zones.
- A car may send several **independent** tasks at once. Each one is placed on its own.
- **Anchor zone** = the zone the car is in when it sends the task. The anchor owns the task until the car confirms it received the result.
- **Fog-to-fog** happens for only two reasons: the car is leaving (mobility), or the anchor is full.

## Flow of one task

```
Car ──(1) task──► Anchor zone (Z1)
                    │
                    ├─(2) TOF-Broker: heavy task? ──yes──► Cloud
                    │
                    ├─(3) D3QN agent picks ONE target:
                    │       Z1 itself │ neighbour Zn │ Cloud
                    │
                    ├─(4) input sent to target (backhaul / WAN)
                    ▼
                 Target runs the whole task
                    │
                    ├─(5) result ──► car's CURRENT zone ──► Car
                    │
Car ──(6) ack──► Anchor closes task, computes reward, agent learns
```

1. **Intake.** The car sends the task to the zone it is in. That zone becomes the anchor and keeps a copy of the input for retries.
2. **TOF-Broker.** Heavy tasks (boulders) go straight to the cloud. Light tasks (pebbles) go to the agent.
3. **Decision.** The anchor's agent uses its own queue, the neighbours' latest state and the predicted zone the car will be in. It picks one target.
4. **Transfer.** If the target is not the anchor, the input travels over the backhaul (to a fog zone) or the WAN (to the cloud).
5. **Delivery.** The result reaches the zone the car is in now. That zone delivers it over the radio.
6. **Close.** The car acks. The anchor records on time, late or dropped, gives the reward to its agent, and deletes the input.

## While the task runs

- Every zone publishes the cars it serves (`car/{id}/attach`) and their GPS.
- The anchor follows its car's GPS wherever the car is.
- If the car is in a coverage gap at delivery time, the anchor keeps the result and resends it when the car next attaches.
- If execution fails, the anchor retries from its stored input if the deadline still allows it. Otherwise the task is dropped.

## [OPEN] Step 5: how the result gets back

| Option | Path | Pros | Cons |
|---|---|---|---|
| A (old docs) | Target → Anchor → car's zone → Car | Anchor sees everything | Extra hop |
| B (proposed) | Target publishes `car/{id}/result` once. The car's zone **and** the anchor both receive it. | One hop. Anchor still keeps the copy and gets the ack. | None significant |

Decision needed: **A or B.**
