from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from pcnme.core.config import load_settings, resolve_first_existing
from pcnme.core.topology import CloudNode, FogNode, Position, Topology
from pcnme.core.config import Settings
from pcnme.optimizer.pretrain import run_offline_pretrain
from pcnme.utils.logging import configure_logging


def _find_case_study_config(case_study: str) -> Optional[Path]:
    cwd = Path.cwd()
    candidates = []
    for up in [cwd] + list(cwd.parents)[:4]:
        candidates.append(up / "case_studies" / case_study / "config.yaml")
    return resolve_first_existing(candidates)


def _topology_from_yaml(data: dict, *, default_fog_mips: int, default_cloud_mips: int, coverage_radius_m: float) -> Topology:
    fog_nodes_cfg = data.get("fog_nodes") or []
    fog_nodes: list[FogNode] = []
    for fog in fog_nodes_cfg:
        fog_nodes.append(
            FogNode(
                id=str(fog["id"]),
                name=str(fog.get("name") or fog["id"]),
                pos=Position(x=float(fog["pos"][0]), y=float(fog["pos"][1]), lat=fog.get("lat"), lon=fog.get("lon")),
                mips=int(fog.get("mips", default_fog_mips)),
                initial_load=float(fog.get("initial_load", fog.get("load", 0.3))),
            )
        )

    cloud_cfg = data.get("cloud") or {"name": "Cloud", "MIPS": default_cloud_mips}
    cloud = CloudNode(name=str(cloud_cfg.get("name", "Cloud")), mips=int(cloud_cfg.get("MIPS", default_cloud_mips)))
    return Topology(fog_nodes=fog_nodes, cloud=cloud, fog_coverage_radius_m=float(coverage_radius_m))


@click.group()
def cli():
    """PCNME command line."""


@cli.command("validate")
@click.option("--config", "config_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--env-file", type=click.Path(path_type=Path, exists=True), default=None)
def validate_cmd(config_path: Path, env_file: Optional[Path]):
    """Validate a YAML config file."""
    if env_file:
        load_dotenv(dotenv_path=env_file)
    settings = load_settings(config_path=config_path, env_file=env_file)

    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    coverage = float(data.get("fog_coverage_radius", settings.FOG_COVERAGE_RADIUS))
    topology = _topology_from_yaml(
        data,
        default_fog_mips=settings.FOG_MIPS,
        default_cloud_mips=settings.CLOUD_MIPS,
        coverage_radius_m=coverage,
    )

    click.echo("OK: config validated")
    click.echo(f"Fog nodes: {len(topology.fog_nodes)}")
    click.echo(f"Fog coverage radius: {topology.fog_coverage_radius_m} m")


@cli.command("pretrain")
@click.option("--case-study", type=str, default=None, help="Run pretrain using a built-in case study")
@click.option("--config", "config_path", type=click.Path(path_type=Path, exists=True), default=None)
@click.option("--batches", type=int, default=10)
@click.option("--batch-size", type=int, default=100)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=Path("results"))
@click.option("--env-file", type=click.Path(path_type=Path, exists=True), default=None)
def pretrain_cmd(
    case_study: Optional[str],
    config_path: Optional[Path],
    batches: int,
    batch_size: int,
    out_dir: Path,
    env_file: Optional[Path],
):
    """Run offline NSGA-II + MMDE pretraining (optimizer checkpoint)."""
    if env_file:
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    if case_study and config_path:
        raise click.UsageError("Use either --case-study or --config, not both")

    if not case_study and not config_path:
        raise click.UsageError("Provide --case-study or --config to define the topology")

    if case_study:
        cfg = _find_case_study_config(case_study)
        if not cfg:
            raise click.ClickException(f"Could not find case study config for {case_study}")
        config_path = cfg

    settings = load_settings(config_path=config_path, env_file=env_file)
    logger = configure_logging(log_dir=out_dir / "logs")

    topo_overrides = {}
    if config_path:
        import yaml

        topo_overrides = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    coverage = float(topo_overrides.get("fog_coverage_radius", settings.FOG_COVERAGE_RADIUS))
    topology = _topology_from_yaml(
        topo_overrides,
        default_fog_mips=settings.FOG_MIPS,
        default_cloud_mips=settings.CLOUD_MIPS,
        coverage_radius_m=coverage,
    )

    logger.info("pretrain_started", batches=int(batches), batch_size=int(batch_size))
    outputs = run_offline_pretrain(
        settings=settings,
        topology=topology,
        batches=int(batches),
        batch_size=int(batch_size),
        out_dir=out_dir,
    )
    logger.info("pretrain_completed", batches=len(outputs), out=str(out_dir))

    # Print a short summary
    last = outputs[-1]
    click.echo(f"OK: wrote {len(outputs)} Pareto snapshots to {out_dir}")
    click.echo(f"Last knee point: idx={last.knee.index}, latency={last.knee.point[0]:.3f}, energy={last.knee.point[1]:.6f}")


@cli.command("train-agent1")
@click.option("--case-study", type=str, default=None)
@click.option("--config", "config_path", type=click.Path(path_type=Path, exists=True), default=None)
@click.option("--batches", type=int, default=10)
@click.option("--batch-size", type=int, default=100)
@click.option("--epochs", type=int, default=3)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=Path("results"))
@click.option("--seed", type=int, default=42)
@click.option("--env-file", type=click.Path(path_type=Path, exists=True), default=None)
def train_agent1_cmd(
    case_study: Optional[str],
    config_path: Optional[Path],
    batches: int,
    batch_size: int,
    epochs: int,
    out_dir: Path,
    seed: int,
    env_file: Optional[Path],
):
    """Behavior-clone Agent1 (placement) from offline optimizer labels."""
    if env_file:
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    if case_study and config_path:
        raise click.UsageError("Use either --case-study or --config, not both")
    if not case_study and not config_path:
        raise click.UsageError("Provide --case-study or --config to define the topology")

    if case_study:
        cfg = _find_case_study_config(case_study)
        if not cfg:
            raise click.ClickException(f"Could not find case study config for {case_study}")
        config_path = cfg

    settings = load_settings(config_path=config_path, env_file=env_file)
    logger = configure_logging(log_dir=out_dir / "logs")

    import yaml

    topo_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path else {}
    topo_data = topo_data or {}
    coverage = float(topo_data.get("fog_coverage_radius", settings.FOG_COVERAGE_RADIUS))
    topology = _topology_from_yaml(
        topo_data,
        default_fog_mips=settings.FOG_MIPS,
        default_cloud_mips=settings.CLOUD_MIPS,
        coverage_radius_m=coverage,
    )

    from pcnme.agents.agent1 import train_agent1_bc

    out_path = out_dir / "agent1.pt"
    logger.info("agent1_bc_started", batches=int(batches), batch_size=int(batch_size), epochs=int(epochs), out=str(out_path))
    try:
        _, result, build = train_agent1_bc(
            settings=settings,
            topology=topology,
            batches=int(batches),
            batch_size=int(batch_size),
            epochs=int(epochs),
            seed=int(seed),
            out_path=out_path,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    logger.info("agent1_bc_completed", samples=int(build.samples), final_loss=float(result.final_loss), out=str(out_path))
    click.echo(f"OK: trained Agent1 BC on {build.samples} samples")
    click.echo(f"Saved: {out_path}")


@cli.command("train-agent2")
@click.option("--samples", type=int, default=5000)
@click.option("--epochs", type=int, default=3)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=Path("results"))
@click.option("--seed", type=int, default=42)
@click.option("--env-file", type=click.Path(path_type=Path, exists=True), default=None)
def train_agent2_cmd(samples: int, epochs: int, out_dir: Path, seed: int, env_file: Optional[Path]):
    """Behavior-clone Agent2 (SDN routing) from a deterministic routing heuristic."""
    if env_file:
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    settings = Settings(_env_file=str(env_file) if env_file else None)
    logger = configure_logging(log_dir=out_dir / "logs")
    from pcnme.agents.agent2 import train_agent2_bc

    out_path = out_dir / "agent2.pt"
    logger.info("agent2_bc_started", samples=int(samples), epochs=int(epochs), out=str(out_path))
    try:
        _, result, build = train_agent2_bc(
            settings=settings,
            samples=int(samples),
            epochs=int(epochs),
            seed=int(seed),
            out_path=out_path,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    logger.info("agent2_bc_completed", samples=int(build.samples), final_loss=float(result.final_loss), out=str(out_path))
    click.echo(f"OK: trained Agent2 BC on {build.samples} samples")
    click.echo(f"Saved: {out_path}")


@cli.command("serve")
@click.option("--case-study", type=str, default=None)
@click.option("--config", "config_path", type=click.Path(path_type=Path, exists=True), default=None)
@click.option("--host", type=str, default=None)
@click.option("--port", type=int, default=None)
@click.option("--reload", is_flag=True, default=False)
@click.option("--env-file", type=click.Path(path_type=Path, exists=True), default=None)
def serve_cmd(
    case_study: Optional[str],
    config_path: Optional[Path],
    host: Optional[str],
    port: Optional[int],
    reload: bool,
    env_file: Optional[Path],
):
    """Run the FastAPI runtime server (requires Redis)."""
    if env_file:
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    if case_study and config_path:
        raise click.UsageError("Use either --case-study or --config, not both")
    if not case_study and not config_path:
        raise click.UsageError("Provide --case-study or --config to define the topology")

    if case_study:
        cfg = _find_case_study_config(case_study)
        if not cfg:
            raise click.ClickException(f"Could not find case study config for {case_study}")
        config_path = cfg

    settings = load_settings(config_path=config_path, env_file=env_file)

    import yaml

    topo_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path else {}
    topo_data = topo_data or {}
    coverage = float(topo_data.get("fog_coverage_radius", settings.FOG_COVERAGE_RADIUS))
    topology = _topology_from_yaml(
        topo_data,
        default_fog_mips=settings.FOG_MIPS,
        default_cloud_mips=settings.CLOUD_MIPS,
        coverage_radius_m=coverage,
    )

    from pcnme.runtime.app import create_app

    app = create_app(settings=settings, topology=topology)

    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover
        raise click.ClickException("uvicorn is required to run the server. Install with `pip install uvicorn[standard]`.") from exc

    uvicorn.run(
        app,
        host=str(host or settings.API_HOST),
        port=int(port or settings.API_PORT),
        reload=bool(reload),
    )


if __name__ == "__main__":
    cli()
