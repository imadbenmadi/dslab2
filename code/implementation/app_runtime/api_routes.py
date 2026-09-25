"""Flask route registration for UnifiedSmartCityApp."""

import threading
from flask import request


def register_runtime_routes(app_state) -> None:
    """Attach runtime API routes to app_state.flask_app."""

    @app_state.flask_app.route("/api/retrain", methods=["POST"])
    def trigger_retrain():
        if app_state.retraining_in_progress:
            return {"status": "already training"}, 202
        app_state.retraining_in_progress = True
        t = threading.Thread(target=app_state._retrain_agents_online, daemon=True)
        t.start()
        app_state._log_event("info", "retraining_triggered")
        return {"status": "retraining started"}, 202

    @app_state.flask_app.route("/api/training-status", methods=["GET"])
    def get_training_status():
        return {
            "retraining": app_state.retraining_in_progress,
            "batch_count": app_state.training_batch_count,
        }, 200

    @app_state.flask_app.route("/api/system-type", methods=["GET"])
    def get_system_type():
        return {"system_type": app_state.system_type}, 200

    @app_state.flask_app.route("/api/map/live", methods=["GET"])
    def get_live_map():
        return app_state.map_state, 200

    @app_state.flask_app.route("/api/agents/analytics", methods=["GET"])
    def get_agents_analytics():
        return {
            "systemType": app_state.system_type,
            "behavioralCloning": {
                "agent1": {
                    "enabled": True,
                    "status": "bootstrapped" if app_state.bc_bootstrap_status["completed"] else "warm-start capable",
                    "description": "Agent1 supports behavioral cloning pretraining via supervised state-action pairs.",
                },
                "agent2": {
                    "enabled": True,
                    "status": "bootstrapped" if app_state.bc_bootstrap_status["completed"] else "warm-start capable",
                    "description": "Agent2 supports behavioral cloning pretraining via supervised routing action labels.",
                },
                "bootstrap": app_state.bc_bootstrap_status,
            },
            "nsgaResults": app_state.nsga_summary,
            "current": app_state._build_agent_snapshot(),
            "history": list(app_state.agent_history),
        }, 200

    @app_state.flask_app.route("/api/control/policy", methods=["GET", "POST"])
    def control_policy():
        if app_state.system_type and request.method == "POST":
            patch = (request.get_json() or {}).get("rules", {})
            updated = app_state.policy_service.update_rules(patch)
            app_state.vehicle_policy.sync(updated)
            app_state.fog_policy.sync(updated)
            return {"status": "updated", "bundle": updated}, 200
        return {"bundle": app_state.policy_service.get_bundle().__dict__}, 200

    @app_state.flask_app.route("/api/control/features", methods=["POST"])
    def control_features():
        patch = (request.get_json() or {}).get("features", {})
        updated = app_state.policy_service.update_features(patch)
        app_state.vehicle_policy.sync(updated)
        app_state.fog_policy.sync(updated)
        return {"status": "updated", "bundle": updated}, 200

    @app_state.flask_app.route("/api/control/fleet", methods=["POST"])
    def control_fleet():
        patch = (request.get_json() or {}).get("fleet", {})
        updated = app_state.policy_service.update_fleet(patch)
        return {"status": "updated", "bundle": updated}, 200

    @app_state.flask_app.route("/api/control/bus", methods=["GET"])
    def control_bus_status():
        topic = request.args.get("topic", default="", type=str).strip()
        recent = app_state.event_bus.peek_topic(topic, limit=20) if topic else []
        return {
            "bus": app_state.event_bus.status(),
            "vehicleBuffer": app_state.vehicle_store_forward.size(),
            "fogBuffer": app_state.fog_store_forward.size(),
            "recent": recent,
        }, 200
