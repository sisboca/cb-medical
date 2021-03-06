# Copyright 2017 Creu Blanca
# Copyright 2017 Eficent Business and IT Consulting Services, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Medical Administration Location",
    "version": "12.0.1.0.0",
    "category": "Medical",
    "website": "https://github.com/OCA/vertical-medical",
    "author": "Creu Blanca, Eficent",
    "license": "LGPL-3",
    "depends": ["medical_administration_location"],
    "data": [
        "security/medical_security.xml",
        "data/ir_sequence_data.xml",
        "views/res_partner_views.xml",
        "views/medical_menu.xml",
    ],
    "demo": ["demo/medical_demo.xml"],
    "installable": True,
    "application": False,
}
