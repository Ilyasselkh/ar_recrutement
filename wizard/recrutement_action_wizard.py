from odoo import models, fields, api, _


class ARDemandeRecrutementActionWizard(models.TransientModel):
    _name = "ar.demande.recrutement.action.wizard"
    _description = "Confirmation action demande recrutement"

    demande_id = fields.Many2one(
        "ar.demande.de.recrutement",
        string="Demande",
        required=True
    )

    action_type = fields.Selection([
        ("modify", "Modifier"),
        ("submit", "Soumettre"),
        ("validate_n1", "Valider N+1"),
        ("validate_rh", "Valider RH"),
        ("validate_md", "Valider MD"),
        ("validate_direction_generale", "Valider Direction générale"),
        ("validate_periode_essai_n1", "Valider période d'essai N+1"),
        ("validate_deliberation_finale", "Valider délibération finale"),
        ("offer_accept", "Accepter l'offre"),
        ("offer_refuse", "Refuser l'offre"),
        ("refuse", "Refuser"),
    ], string="Type d'action", required=True)

    message = fields.Text(
        string="Message",
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        action_type = res.get("action_type") or self.env.context.get("default_action_type")
        demande_id = res.get("demande_id") or self.env.context.get("default_demande_id")

        if demande_id:
            res["demande_id"] = demande_id

        if action_type:
            res["action_type"] = action_type

        messages = {
            "modify": _(
                "Merci de confirmer la modification de cette demande. "
                "Cette action réinitialisera le circuit de validation et relancera le workflow depuis le début."
            ),
            "submit": _(
                "Merci de confirmer la soumission de cette demande."
            ),
            "validate_n1": _(
                "Merci de confirmer la validation de cette demande au niveau N+1."
            ),
            "validate_rh": _(
                "Merci de confirmer la validation de cette demande au niveau RH."
            ),
            "validate_md": _(
                "Merci de confirmer la validation de cette demande au niveau MD."
            ),
            "validate_direction_generale": _(
                "Merci de confirmer la validation de cette demande au niveau Direction générale."
            ),
            "validate_periode_essai_n1": _(
                "Merci de confirmer la validation de cette demande au niveau Période d'essai N+1."
            ),
            "validate_deliberation_finale": _(
                "Merci de confirmer la validation de cette demande au niveau Délibération finale."
            ),
            "offer_accept": _(
                "Merci de confirmer l'acceptation de l'offre. Le flux continuera vers l'etape Date d'embauche."
            ),
            "offer_refuse": _(
                "Merci de confirmer le refus de l'offre. Le flux retournera à l'étape CVthèques."
            ),
            "refuse": _(
                "Merci de confirmer le refus de cette demande."
            ),
        }

        res["message"] = messages.get(action_type, _("Merci de confirmer cette action."))
        return res

    def action_confirm(self):
        self.ensure_one()

        if self.action_type == "modify":
            self.demande_id.action_demander_modification()

        elif self.action_type == "submit":
            self.demande_id.action_soumettre()

        elif self.action_type == "validate_n1":
            self.demande_id.action_valider_n1()

        elif self.action_type == "validate_rh":
            self.demande_id.action_valider_rh()

        elif self.action_type == "validate_md":
            self.demande_id.action_valider_md()

        elif self.action_type == "validate_direction_generale":
            self.demande_id.action_valider_direction_generale()

        elif self.action_type == "validate_deliberation_finale":
            self.demande_id.action_valider_deliberation_finale()

        elif self.action_type == "validate_periode_essai_n1":
            self.demande_id.action_valider_periode_essai_n1()

        elif self.action_type == "offer_accept":
            self.demande_id.action_offre_acceptee()

        elif self.action_type == "offer_refuse":
            self.demande_id.action_offre_refusee()

        elif self.action_type == "refuse":
            self.demande_id.action_refuser()

        return {"type": "ir.actions.act_window_close"}

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}
