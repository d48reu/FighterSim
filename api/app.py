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
    # Game State
    # ------------------------------------------------------------------

    @app.route("/api/gamestate")
    def get_gamestate():
        return jsonify(services.get_gamestate())

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
    # Event booking
    # ------------------------------------------------------------------

    @app.route("/api/events/bookable-fighters")
    def bookable_fighters():
        return jsonify(services.get_bookable_fighters())

    @app.route("/api/events/venues")
    def list_venues():
        return jsonify(services.get_venues())

    @app.route("/api/events/create", methods=["POST"])
    def create_event():
        data = request.json
        result = services.create_event(
            name=data["name"],
            venue=data["venue"],
            event_date_str=data["event_date"],
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/events/scheduled")
    def scheduled_events():
        return jsonify(services.get_scheduled_events())

    @app.route("/api/events/history")
    def event_history():
        limit = int(request.args.get("limit", 20))
        return jsonify(services.get_event_history(limit))

    @app.route("/api/events/<int:event_id>")
    def get_event(event_id: int):
        event = services.get_event(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404
        return jsonify(event)

    @app.route("/api/events/<int:event_id>/add-fight", methods=["POST"])
    def add_fight_to_event(event_id: int):
        data = request.json
        result = services.add_fight_to_event(
            event_id=event_id,
            fighter_a_id=data["fighter_a_id"],
            fighter_b_id=data["fighter_b_id"],
            is_title_fight=data.get("is_title_fight", False),
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/events/<int:event_id>/fights/<int:fight_id>", methods=["DELETE"])
    def remove_fight_from_event(event_id: int, fight_id: int):
        result = services.remove_fight_from_event(event_id, fight_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/events/<int:event_id>/projection")
    def event_projection(event_id: int):
        result = services.calculate_event_projection(event_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/events/<int:event_id>/simulate", methods=["POST"])
    def simulate_player_event(event_id: int):
        task_id = services.start_simulate_player_event(event_id)
        return jsonify({"task_id": task_id, "status": "pending"})

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

    @app.route("/api/news")
    def news_feed():
        limit = int(request.args.get("limit", 15))
        return jsonify(services.get_news_feed(limit))

    @app.route("/api/fighters/<int:fighter_id>/timeline")
    def fighter_timeline(fighter_id: int):
        result = services.get_fighter_timeline(fighter_id)
        if result is None:
            return jsonify({"error": "Fighter not found"}), 404
        return jsonify(result)

    @app.route("/api/fighters/<int:fighter_id>/nickname-suggestions")
    def nickname_suggestions(fighter_id: int):
        suggestions = services.get_nickname_suggestions(fighter_id)
        return jsonify({"suggestions": suggestions})

    @app.route("/api/fighters/<int:fighter_id>/nickname", methods=["POST"])
    def set_nickname(fighter_id: int):
        data = request.json
        result = services.set_nickname(fighter_id, data.get("nickname", ""))
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/events/<int:event_id>/press-conference", methods=["POST"])
    def press_conference(event_id: int):
        result = services.hold_press_conference(event_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    # ------------------------------------------------------------------
    # Cornerstone Fighters
    # ------------------------------------------------------------------

    @app.route("/api/cornerstones")
    def list_cornerstones():
        return jsonify(services.get_cornerstones())

    @app.route("/api/cornerstones/designate", methods=["POST"])
    def designate_cornerstone():
        data = request.json
        result = services.designate_cornerstone(data["fighter_id"])
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/cornerstones/remove", methods=["POST"])
    def remove_cornerstone():
        data = request.json
        result = services.remove_cornerstone(data["fighter_id"])
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

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
    # Broadcast Deals
    # ------------------------------------------------------------------

    @app.route("/api/broadcast/available")
    def broadcast_available():
        result = services.get_available_deals()
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/broadcast/active")
    def broadcast_active():
        return jsonify(services.get_active_deal())

    @app.route("/api/broadcast/negotiate", methods=["POST"])
    def broadcast_negotiate():
        data = request.json
        result = services.negotiate_deal(data["tier"])
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)

    # ------------------------------------------------------------------
    # Rival Info
    # ------------------------------------------------------------------

    @app.route("/api/rival")
    def get_rival():
        result = services.get_rival_info()
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    # ------------------------------------------------------------------
    # Sponsorships
    # ------------------------------------------------------------------

    @app.route("/api/sponsorships/fighter/<int:fighter_id>")
    def fighter_sponsorships(fighter_id: int):
        result = services.get_fighter_sponsorships(fighter_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/sponsorships/seek", methods=["POST"])
    def seek_sponsorship():
        data = request.json
        result = services.seek_sponsorship(
            fighter_id=data["fighter_id"],
            tier=data["tier"],
        )
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/sponsorships/summary")
    def sponsorship_summary():
        return jsonify(services.get_sponsorship_summary())

    # ------------------------------------------------------------------
    # Reality Show
    # ------------------------------------------------------------------

    @app.route("/api/show/eligible-fighters")
    def show_eligible_fighters():
        weight_class = request.args.get("weight_class")
        if not weight_class:
            return jsonify({"error": "weight_class parameter required"}), 400
        return jsonify(services.get_show_eligible_fighters(weight_class))

    @app.route("/api/show/create", methods=["POST"])
    def create_show():
        data = request.json
        result = services.create_reality_show(
            name=data["name"],
            weight_class=data["weight_class"],
            format_size=data["format_size"],
            fighter_ids=data["fighter_ids"],
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/show/active")
    def active_show():
        return jsonify(services.get_active_show())

    @app.route("/api/show/<int:show_id>")
    def show_details(show_id: int):
        result = services.get_show_details(show_id)
        if "error" in result:
            return jsonify(result), 404
        return jsonify(result)

    @app.route("/api/show/<int:show_id>/bracket")
    def show_bracket(show_id: int):
        result = services.get_show_bracket(show_id)
        if "error" in result:
            return jsonify(result), 404
        return jsonify(result)

    @app.route("/api/show/history")
    def show_history():
        return jsonify(services.get_show_history())

    @app.route("/api/show/<int:show_id>/cancel", methods=["POST"])
    def cancel_show(show_id: int):
        result = services.cancel_show(show_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/show/<int:show_id>/sign-winner", methods=["POST"])
    def sign_show_winner(show_id: int):
        result = services.sign_show_winner(show_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/show/<int:show_id>/contestants")
    def show_contestants(show_id: int):
        return jsonify(services.get_show_contestants_for_signing(show_id))

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

    # ------------------------------------------------------------------
    # Fighter Development
    # ------------------------------------------------------------------

    @app.route("/api/development/camps")
    def development_camps():
        return jsonify(services.get_training_camps())

    @app.route("/api/development/roster")
    def development_roster():
        return jsonify(services.get_roster_development())

    @app.route("/api/development/assign", methods=["POST"])
    def development_assign():
        data = request.json
        result = services.assign_fighter_to_camp(
            fighter_id=data["fighter_id"],
            camp_id=data["camp_id"],
            focus=data["focus"],
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/development/remove", methods=["POST"])
    def development_remove():
        data = request.json
        result = services.remove_fighter_from_camp(data["fighter_id"])
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/api/development/projection")
    def development_projection():
        fighter_id = request.args.get("fighter_id", type=int)
        camp_id = request.args.get("camp_id", type=int)
        focus = request.args.get("focus", "Balanced")
        months = request.args.get("months", 12, type=int)
        if not fighter_id or not camp_id:
            return jsonify({"error": "fighter_id and camp_id are required."}), 400
        result = services.get_development_projections(fighter_id, camp_id, focus, months)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    return app
