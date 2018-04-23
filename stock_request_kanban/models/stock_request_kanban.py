# Copyright 2018 Creu Blanca
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, models, fields
from odoo.addons import decimal_precision as dp


class StockRequestKanban(models.Model):
    _name = 'stock.request.kanban'
    _description = 'Stock Request Kanban'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        warehouse = None
        if 'warehouse_id' not in res and res.get('company_id'):
            warehouse = self.env['stock.warehouse'].search(
                [('company_id', '=', res['company_id'])], limit=1)
        if warehouse:
            res['warehouse_id'] = warehouse.id
            res['location_id'] = warehouse.lot_stock_id.id
        return res

    name = fields.Char(
        'Name', copy=False, required=True,
        default='/'
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        ondelete="cascade", required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'stock.request.kanban'),
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse',
        ondelete="cascade", required=True,
    )
    location_id = fields.Many2one(
        'stock.location', 'Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        ondelete="cascade", required=True,
    )
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])], ondelete='cascade',
        required=True,
    )
    product_uom_id = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        required=True,
        default=lambda self: self._context.get('product_uom_id', False),
    )
    product_uom_qty = fields.Float(
        'Quantity', digits=dp.get_precision('Product Unit of Measure'),
        required=True,
        help="Quantity, specified in the unit of measure indicated in the "
             "request.",
    )
    product_qty = fields.Float(
        'Real Quantity', compute='_compute_product_qty',
        store=True, readonly=True, copy=False,
        help='Quantity in the default UoM of the product',
    )
    route_id = fields.Many2one('stock.location.route', string='Route',
                               domain="[('id', 'in', route_ids)]",
                               ondelete='restrict')
    route_ids = fields.Many2many(
        'stock.location.route', string='Route',
        compute='_compute_route_ids',
        readonly=True,
    )
    procurement_group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        help="Moves created through this stock request will be put in this "
             "procurement group. If none is given, the moves generated by "
             "procurement rules will be grouped into one big picking.",
    )

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_product_qty(self):
        self.product_qty = self.product_uom_id._compute_quantity(
            self.product_uom_qty, self.product_id.uom_id)

    @api.depends('product_id', 'warehouse_id', 'location_id')
    def _compute_route_ids(self):
        for record in self:
            routes = self.env['stock.location.route']
            if record.product_id:
                routes += record.product_id.mapped(
                    'route_ids') | record.product_id.mapped(
                    'categ_id').mapped('total_route_ids')
            if record.warehouse_id:
                routes |= self.env['stock.location.route'].search(
                    [('warehouse_ids', 'in', record.warehouse_id.ids)])
            parents = record.get_parents().ids
            record.route_ids = routes.filtered(lambda r: any(
                p.location_id.id in parents for p in r.pull_ids))

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = {'domain': {}}
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            res['domain']['product_uom_id'] = [
                ('category_id', '=', self.product_id.uom_id.category_id.id)]
            return res
        res['domain']['product_uom_id'] = []
        return res

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        """ Finds location id for changed warehouse. """
        res = {'domain': {}}
        if self.warehouse_id:
            # search with sudo because the user may not have permissions
            loc_wh = self.location_id.sudo().get_warehouse()
            if self.warehouse_id != loc_wh:
                self.location_id = self.warehouse_id.lot_stock_id.id
            if self.warehouse_id.company_id != self.company_id:
                self.company_id = self.warehouse_id.company_id
        return res

    @api.onchange('location_id')
    def onchange_location_id(self):
        res = {'domain': {}}
        if self.location_id:
            loc_wh = self.location_id.sudo().get_warehouse()
            if loc_wh and self.warehouse_id != loc_wh:
                self.warehouse_id = loc_wh
                self.onchange_warehouse_id()
        return res

    @api.onchange('company_id')
    def onchange_company_id(self):
        """ Sets a default warehouse when the company is changed and limits
        the user selection of warehouses. """
        if self.company_id and (
            not self.warehouse_id or
            self.warehouse_id.company_id != self.company_id
        ):
            self.warehouse_id = self.env['stock.warehouse'].search(
                [('company_id', '=', self.company_id.id)], limit=1)
            self.onchange_warehouse_id()

        return {
            'domain': {
                'warehouse_id': [('company_id', '=', self.company_id.id)]}}

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'stock.request.kanban')
        return super().create(vals)

    def get_parents(self):
        location = self.location_id.sudo()
        result = location
        while location.location_id:
            location = location.location_id
            result |= location
        return result
