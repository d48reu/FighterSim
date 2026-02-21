"""Flask app factory for FighterSim."""

from pathlib import Path

from flask import Flask, jsonify, request, render_template

from api import services

ROOT = Path(__file__).parent.parent


def create_app(db_url: str = "sqlite:///mma_test.db") -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ROOT / "frontend" / "templates"),
        static_folder=str(ROOT / "frontend" / "static"),
        static_url_path="/static",
    )

    services.init_db(db_url)

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return render_template("index.html")

    # ------------------------------------------------------------------
    # Fighters
    # ------------------------------------------------------------------

    @app.route("/api/fighters")
    def list_fighters():
        weight_class = request.args.get("weight_class")
        limit = int(request.args.get("limit", 200))
        return jsonify(services.get_fighters(weight_class, limit))

    @app.route("/api/fighters/<int:fighter_id>")
    def get_fighter(fighter_id: int):
        fighter = services.get_fighter(fighter_id)
        if not fighter:
            return jsonify({"error": "Fighter not found"}), 404
        return jsonify(fighter)

    # ------------------------------------------------------------------
    # Organization
    # ------------------------------------------------------------------

    @app.route("/api/organization")
    def get_organization():
        org = services.get_player_org()
        if not org:
            return jsonify({"error": "No player organization found"}), 404
        return jsonify(org)

    # ------------------------------------------------------------------
    # Rankings
    # ------------------------------------------------------------------

    @app.route("/api/rankings/<weight_class>")
    def get_rankings(weight_class: str):
        return jsonify(services.get_rankings_for_class(weight_class))

    # ------------------------------------------------------------------
    # Async: simulate event
    # ------------------------------------------------------------------

    @app.route("/api/events/simulate", methods=["POST"])
    def simulate_event():
        task_id = services.start_simulate_event()
        return jsonify({"task_id": task_id, "status": "pending"})

    # ------------------------------------------------------------------
    # Async: advance month
    # ------------------------------------------------------------------

    @app.route("/api/sim/month", methods=["POST"])
    def advance_month():
        task_id = services.start_advance_month()
        return jsonify({"task_id": task_id, "status": "pending"})

    # ------------------------------------------------------------------
    # Task polling
    # ------------------------------------------------------------------

    @app.route("/api/tasks/<task_id>")
    def get_task(task_id: str):
        task = services.get_task(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task)

    # ------------------------------------------------------------------
    # Narrative
    # ------------------------------------------------------------------

    @app.route("/api/fighters/<int:fighter_id>/bio")
    def fighter_bio(fighter_id: int):
        bio = services.get_fighter_bio(fighter_id)
        if bio is None:
            return jsonify({"error": "Fighter not found"}), 404
        return jsonify({"bio": bio})

    @app.route("/api/fighters/<int:fighter_id>/tags")
    def fighter_tags(fighter_id: int):
        tags = services.get_fighter_tags(fighter_id)
        if tags is None:
            return jsonify({"error": "Fighter not found"}), 404
        return jsonify({"tags": tags})

    @app.route("/api/goat")
    def goat_scores():
        top_n = int(request.args.get("top", 10))
        return jsonify(services.get_goat_scores(top_n))

    @app.route("/api/rivalries")
    def rivalries():
        return jsonify(services.get_rivalries())

    # ------------------------------------------------------------------
    # Contract negotiation
    # ------------------------------------------------------------------

    @app.route("/api/free-agents")
    def list_free_agents():
        weight_class = request.args.get("weight_class")
        style = request.args.get("style")
        min_overall = request.args.get("min_overall", type=int)
        sort_by = request.args.get("sort_by")
        return jsonify(services.get_free_agents(weight_class, style, min_overall, sort_by))

    @app.route("/api/roster")
    def list_roster():
        return jsonify(services.get_roster())

    @app.route("/api/contracts/offer", methods=["POST"])
    def contract_offer():
        data = request.json
        result = services.make_contract_offer(
            fighter_id=data["fighter_id"],
            salary=data["salary"],
            fight_count=data["fight_count"],
            length_months=data["length_months"],
        )
        return jsonify(result)

    @app.route("/api/contracts/release", methods=["POST"])
    def contract_release():
        data = request.json
        result = services.release_fighter(data["fighter_id"])
        return jsonify(result)

    @app.route("/api/contracts/expiring")
    def expiring_contracts():
        return jsonify(services.get_expiring_contracts())

    @app.route("/api/contracts/renew", methods=["POST"])
    def contract_renew():
        data = request.json
        result = services.renew_contract(
            fighter_id=data["fighter_id"],
            salary=data["salary"],
            fight_count=data["fight_count"],
            length_months=data["length_months"],
        )
        return jsonify(result)

    @app.route("/api/finances")
    def finances():
        return jsonify(services.get_finances())

    @app.route("/api/notifications")
    def notifications():
        return jsonify(services.get_notifications())

    @app.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
    def mark_notification_read(notif_id: int):
        return jsonify(services.mark_notification_read(notif_id))

    return app
