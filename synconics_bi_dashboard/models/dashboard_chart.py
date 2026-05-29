import io
import csv
import base64
import xlsxwriter
import imgkit
import logging

from math import gcd
from markupsafe import Markup
from types import SimpleNamespace
from collections import defaultdict
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.tools import groupby, format_amount
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class UTCDatetime:
    def __init__(self, dt):
        self.dt = dt

    def to_utc(self):
        return self  # Already handling as UTC

    def strftime(self, fmt):
        return self.dt.strftime(fmt)


def safe_datetime_combine(date_obj, time_obj):
    combined = datetime.combine(date_obj, time_obj)
    return UTCDatetime(combined)


def format_date_by_range(value, time_range):
    if not isinstance(value, (date, datetime)):
        return str(value)  # fallback if it's not a date/datetime

    if time_range == "day":
        return value.strftime("%d %B %Y")  # e.g., "19 June 2025"

    elif time_range == "week":
        return f"Week {value.isocalendar()[1]} {value.year}"  # e.g., "Week 25 2025"

    elif time_range == "month":
        return value.strftime("%B %Y")  # e.g., "June 2025"

    elif time_range == "quarter":
        # Calculate quarter from month
        quarter = (value.month - 1) // 3 + 1
        return f"Q{quarter} {value.year}"  # e.g., "Q2 2025"

    elif time_range == "year":
        return value.strftime("%Y")  # e.g., "2025"

    else:
        return str(value)  # default fallback


class DashboardChart(models.Model):
    _name = "dashboard.chart"
    _description = "Dashboard Charts"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    @api.depends("list_field_ids", "list_field_ids.list_field_id")
    def _compute_used_list_fields(self):
        for rec in self:
            rec.used_list_field_ids = [
                (6, 0, rec.list_field_ids.mapped("list_field_id").ids)
            ]

    name = fields.Char(string="Name", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    dashboard_id = fields.Many2one(
        "dashboard.dashboard",
        string="Dashboard",
        required=True,
        tracking=True,
        ondelete="cascade",
    )
    chart_type = fields.Selection(
        [
            ("kpi", "KPI"),
            ("tile", "Tile View"),
            ("bar_chart", "Bar Chart"),
            ("column_chart", "Column Chart"),
            ("doughnut_chart", "Doughnut Chart"),
            ("area_chart", "Area Chart"),
            ("funnel_chart", "Funnel Chart"),
            ("pyramid_chart", "Pyramid Chart"),
            ("line_chart", "Line Chart"),
            ("pie_chart", "Pie Chart"),
            ("radar_chart", "Radar Chart"),
            ("stackedcolumn_chart", "StackedColumn"),
            ("radial_chart", "Radial Chart"),
            ("scatter_chart", "Scatter Chart"),
            ("map_chart", "Map Chart"),
            ("meter_chart", "Meter Chart"),
            ("to_do", "To Do"),
            ("list", "List View"),
        ],
        default="kpi",
        required=True,
        string="Type",
        tracking=True,
    )

    # KPI fields
    kpi_model_id = fields.Many2one(
        "ir.model", string="Model ", ondelete="set null", tracking=True
    )
    kpi_model = fields.Char(string="Model Ref", related="kpi_model_id.model")
    kpi_data_type = fields.Selection(
        [("count", "Count"), ("sum", "Sum"), ("average", "Average"), ("count_distinct", "Count Distinct")],
        default="sum",
        string="Data Type ",
        tracking=True,
    )
    kpi_measurement_field_id = fields.Many2one(
        "ir.model.fields", string="Measure Field ", ondelete="set null", tracking=True
    )
    kpi_limit_record = fields.Integer(string="Limit Record", default=0)
    kpi_domain = fields.Char(string="Domain ", default="[]")
    kpi_date_filter_field_id = fields.Many2one(
        "ir.model.fields",
        string="Date Filter",
        ondelete="set null",
    )
    meter_target = fields.Integer(string="Target")
    kpi_date_filter_option = fields.Selection(
        [
            ("none", "None"),
            ("today", "Today"),
            ("this_week", "This Week"),
            ("this_month", "This Month"),
            ("this_quarter", "This Quarter"),
            ("this_year", "This Year"),
            ("week_to_date", "Week To Date"),
            ("month_to_date", "Month To Date"),
            ("quarter_to_date", "Quarter To Date"),
            ("year_to_date", "Year To Date"),
            ("next_day", "Next Day"),
            ("next_week", "Next Week"),
            ("next_month", "Next Month"),
            ("next_quarter", "Next Quarter"),
            ("next_year", "Next Year"),
            ("last_day", "Last Day"),
            ("last_week", "Last Week"),
            ("last_month", "Last Month"),
            ("last_quarter", "Last Quarter"),
            ("last_year", "Last Year"),
            ("last_seven_days", "Last Seven Days"),
            ("last_thirty_days", "Last 30 Days"),
            ("last_ninety_days", "Last Ninety Days"),
            ("last_year_days", "Last 365 Days"),
            ("past_till_now", "Past Till Now"),
            ("past_excluding_today", "Past Excluding Today"),
            ("future_starting_today", "Future Starting Today"),
            ("future_starting_now", "Future Starting Now"),
            ("future_starting_tomorrow", "Future Starting Tomorrow"),
        ],
        default="none",
        string="Date Filter Options ",
        tracking=True,
    )
    kpi_include_periods = fields.Integer(string="Include Period ", default=0)
    kpi_same_period_previous_years = fields.Integer(
        string="Same Period Previous Years ", default=0
    )
    kpi_comparison_type = fields.Selection(
        [
            ("none", "None"),
            ("sum", "Sum"),
            ("ratio", "Ratio"),
            ("percentage", "Percentage"),
        ],
        default="none",
        string="Comparison Type",
        tracking=True,
    )
    kpi_enable_target = fields.Boolean(string="Enable Target")
    kpi_target_value = fields.Integer(string="Target Value", default=0)
    kpi_view_type = fields.Selection(
        [("standard", "Standard"), ("progress", "Progress")],
        default="standard",
        string="View",
    )

    # Main data fields
    model_id = fields.Many2one(
        "ir.model", string="Model", ondelete="set null", tracking=True
    )
    model = fields.Char(string="Model Ref.", related="model_id.model")
    measurement_field_ids = fields.Many2many(
        "ir.model.fields",
        "ir_fields_chart_rel",
        "chart_id",
        "field_id",
        string="Measurements",
        tracking=True,
    )

    list_type = fields.Selection(
        [("standard", "Standard"), ("grouped", "Grouped")],
        string="List Type",
        default="standard",
        help="Select group type.",
        tracking=True,
    )
    list_field_ids = fields.One2many(
        "list.fields",
        "field_id",
        string="List Standard Fields",
        copy=True,
        auto_join=True,
        help="Select and add column fields for the standard list view.",
        tracking=True,
    )
    used_list_field_ids = fields.Many2many(
        "ir.model.fields",
        string="Used List Ids",
        compute="_compute_used_list_fields",
        store=True,
    )
    list_measure_ids = fields.One2many(
        "list.fields",
        "measure_id",
        string="List Measure Fields",
        copy=True,
        auto_join=True,
        help="Select and add column fields for the standard list view.",
    )

    todo_layout = fields.Selection(
        [
            ("default", "Default"),
            ("activity", "Activity"),
        ],
        default="default",
        string="To Do Layout",
        help="Select To Do action.",
        tracking=True,
    )
    todo_action_ids = fields.One2many(
        "todo.action",
        "layout_id",
        string="TODO Actions",
        copy=True,
        auto_join=True,
        help="Set action for information purpose.",
    )

    image = fields.Binary(string="Image", help="Set image for mail")
    group_by_id = fields.Many2one(
        "ir.model.fields", string="Group By", ondelete="set null", tracking=True
    )
    group_by_type = fields.Selection(
        related="group_by_id.ttype", string="Group By Type", readonly=True
    )
    time_range = fields.Selection(
        [
            ("day", "Day"),
            ("week", "Week"),
            ("month", "Month"),
            ("quarter", "Quarter"),
            ("year", "Year"),
        ],
        string="Group by Time Range",
        help="Select time range on selected Group by Date option.",
    )

    map_group_by_id = fields.Many2one(
        "ir.model.fields", string="Map Group by", tracking=True
    )
    measurement_field_id = fields.Many2one(
        "ir.model.fields",
        string="Measure Field",
        tracking=True,
        ondelete="set null",
    )
    sub_group_by_id = fields.Many2one(
        "ir.model.fields",
        string="Sub Group By",
        tracking=True,
        ondelete="set null",
    )
    sub_group_by_type = fields.Selection(related="sub_group_by_id.ttype", readonly=True)
    sub_time_range = fields.Selection(
        [
            ("day", "Day"),
            ("week", "Week"),
            ("month", "Month"),
            ("quarter", "Quarter"),
            ("year", "Year"),
        ],
        string="Sub Group by Time Range",
        help="Select time range on selected Sub-Group by Date option.",
    )

    sort_field_id = fields.Many2one(
        "ir.model.fields",
        string="Sort With",
        tracking=True,
        ondelete="set null",
    )
    limit_record = fields.Integer(
        string="Record Limit",
        default=20,
        tracking=True,
        help="If you will change it to 0 (zero) then it will consider all records",
    )
    domain = fields.Char(string="Domain", default="[]")
    sort_order = fields.Selection(
        [("asc", "Ascending"), ("desc", "Descending")],
        string="Sort Order",
        default="asc",
        tracking=True,
    )
    data_type = fields.Selection(
        [("count", "Count"), ("sum", "Sum"), ("average", "Average"), ("count_distinct", "Count Distinct")],
        default="sum",
        string="Data Type",
        tracking=True,
    )
    background_color = fields.Char(string="Background Color", default="#fff")
    is_kpi_border = fields.Boolean(string="Enable Border")
    kpi_border_type = fields.Selection(
        [
            ("none", "None"),
            ("left", "Left"),
            ("right", "Right"),
            ("top", "Top"),
            ("bottom", "Bottom"),
        ],
        default="none",
        string="Border Type",
    )
    kpi_border_color = fields.Char(string="Border Color", default="#fff")
    kpi_border_width = fields.Integer(string="Border Width", default="10")
    font_color = fields.Char(string="Font Color", default="#000")
    layout_type = fields.Selection(
        [
            ("layout1", "Layout 1"),
            ("layout2", "Layout 2"),
            ("layout3", "Layout 3"),
            ("layout4", "Layout 4"),
            ("layout5", "Layout 5"),
        ],
        default="layout1",
        string="Layout",
        required=True,
    )
    tile_layout_type = fields.Selection(
        [
            ("layout1", "Layout 1"),
            ("layout2", "Layout 2"),
            ("layout3", "Layout 3"),
            ("layout4", "Layout 4"),
        ],
        default="layout1",
        string="Layout ",
        required=True,
    )
    # ── Tile group_by ────────────────────────────────────────────────────────
    tile_group_by_id = fields.Many2one(
        "ir.model.fields",
        string="Grouper par",
        ondelete="set null",
        domain="[('model_id', '=', model_id), ('store', '=', True),"
               " ('ttype', 'not in', ['one2many', 'many2many', 'binary', 'html']),"
               " ('name', '!=', 'id')]",
    )
    tile_group_mode = fields.Selection(
        [
            ("single", "Valeur globale"),
            ("grouped", "Liste par groupe"),
            ("top", "Top 1"),
        ],
        string="Mode groupement",
        default="single",
    )
    tile_group_limit = fields.Integer(
        string="Limite groupes",
        default=5,
    )
    text_align = fields.Selection(
        [("left", "Left"), ("center", "Center"), ("right", "Right")],
        string="Text Align",
        default="center",
    )
    theme = fields.Selection(
        [
            ("animated", "Animated"),
            ("frozen", "Frozen"),
            ("kelly", "Kelly"),
            ("material", "Material"),
            ("moonrise", "Moonrise"),
            ("spirited", "Spirited"),
        ],
        default="animated",
        string="Theme",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="dashboard_id.company_id",
        required=True,
    )
    item_view_action_ids = fields.One2many(
        "item.view.action", "chart_id", string="Item Actions"
    )
    item_action_id = fields.Many2one(
        "ir.actions.act_window",
        string="Last Item Action",
        tracking=True,
        ondelete="set null",
    )
    date_filter_field_id = fields.Many2one(
        "ir.model.fields",
        string="Date Filter Field",
        tracking=True,
        ondelete="set null",
    )
    date_filter_option = fields.Selection(
        [
            ("none", "None"),
            ("today", "Today"),
            ("this_week", "This Week"),
            ("this_month", "This Month"),
            ("this_quarter", "This Quarter"),
            ("this_year", "This Year"),
            ("week_to_date", "Week To Date"),
            ("month_to_date", "Month To Date"),
            ("quarter_to_date", "Quarter To Date"),
            ("year_to_date", "Year To Date"),
            ("next_day", "Next Day"),
            ("next_week", "Next Week"),
            ("next_month", "Next Month"),
            ("next_quarter", "Next Quarter"),
            ("next_year", "Next Year"),
            ("last_day", "Last Day"),
            ("last_week", "Last Week"),
            ("last_month", "Last Month"),
            ("last_quarter", "Last Quarter"),
            ("last_year", "Last Year"),
            ("last_seven_days", "Last Seven Days"),
            ("last_thirty_days", "Last 30 Days"),
            ("last_ninety_days", "Last Ninety Days"),
            ("last_year_days", "Last 365 Days"),
            ("past_till_now", "Past Till Now"),
            ("past_excluding_today", "Past Excluding Today"),
            ("future_starting_today", "Future Starting Today"),
            ("future_starting_now", "Future Starting Now"),
            ("future_starting_tomorrow", "Future Starting Tomorrow"),
        ],
        default="none",
        string="Date Filter Options",
        tracking=True,
    )
    is_apply_multiplier = fields.Boolean(
        string="Apply Multiplier", default=False, tracking=True
    )
    chart_multiplier_ids = fields.One2many(
        "chart.multiplier", "chart_id", string="Chart Multiplier"
    )
    include_periods = fields.Integer(string="Include Period", default=0)
    same_period_previous_years = fields.Integer(
        string="Same Period Previous Years", default=0
    )
    icon_option = fields.Selection(
        [("default", "Default"), ("custom", "Custom")],
        default="default",
        string="Icon Option",
    )
    default_icon = fields.Char(string="Default Icon")
    icon = fields.Binary(string="Icon ")
    previous_period_comparision = fields.Boolean(
        string="Previous Period Comparison",
        help="Activate/deactivate previous comparison in KPI layout.",
        tracking=True,
    )
    previous_period_duration = fields.Integer(
        string="Previous Period Duration",
        default=1,
        tracking=True,
        help="Set the value integer to be compared with the configured date filter for the KPI layout. \n For e.g. In date filter it is set to 'This Year' and if you set the value to 2 then 'This year' records will be compared with 2 years back previous records",
    )
    previous_period_type = fields.Selection(
        [("percentage", "Percentage"), ("value", "Value")],
        string="Previous Period Type",
        default="percentage",
        tracking=True,
    )
    show_unit = fields.Boolean("Show Unit", help="Set unit type on axis.")
    unit_type = fields.Selection(
        [("monetary", "Monetary"), ("custom", "Custom")],
        string="Unit Type",
        default="monetary",
        help="Select unit type for axis.",
    )
    custom_unit = fields.Char("Custom Unit", help="Set custom unit type on 'Y' axis.")
    group_ids = fields.Many2many(
        "res.groups",
        "chart_group_rel",
        "chart_id",
        "group_id",
        string="Access Groups",
    )

    button_color = fields.Char(string="Top Button Color")
    font_size = fields.Integer(
        string="Font Size", help="Set font size for Tile", default=35
    )
    font_weight = fields.Selection(
        [
            ("100", "100"),
            ("200", "200"),
            ("300", "300"),
            ("400", "400"),
            ("500", "500"),
            ("600", "600"),
            ("700", "700"),
            ("800", "800"),
            ("900", "900"),
        ],
        string="Font Weight",
        help="Set font thickness for Tile",
        default="600",
    )
    hide_false_value = fields.Boolean(string="Hide False", default=True)

    # ── Multi-dimensional groupby (V0) ────────────────────────────────────────
    # Dimension 1 : champ d'un modèle lié via un Many2one du modèle de base
    #   ex : account.move  --partner_id-->  res.partner  --industry_id-->  secteur
    dim1_link_field_id = fields.Many2one(
        "ir.model.fields",
        string="Dim 1 — Liaison (M2O)",
        ondelete="set null",
        domain="[('model_id','=',model_id),('ttype','=','many2one'),('store','=',True)]",
        help="Champ Many2one du modèle de base vers le modèle lié (ex: partner_id).",
    )
    dim1_related_model_id = fields.Many2one(
        "ir.model",
        string="Dim 1 — Modèle lié",
        compute="_compute_dim1_related_model_id",
        store=True,
    )
    dim1_group_field_id = fields.Many2one(
        "ir.model.fields",
        string="Dim 1 — Grouper par",
        ondelete="set null",
        domain="[('model_id','=',dim1_related_model_id),('store','=',True),"
               "('ttype','not in',['one2many','many2many','binary','html']),"
               "('name','!=','id')]",
        help="Champ du modèle lié servant d'axe de regroupement (ex: industry_id).",
    )

    # Dimension 2 : champ direct OU via un second modèle lié, avec granularité date optionnelle
    enable_dim2 = fields.Boolean(
        string="Activer 2e dimension",
        default=False,
    )
    dim2_link_field_id = fields.Many2one(
        "ir.model.fields",
        string="Dim 2 — Liaison (optionnel)",
        ondelete="set null",
        domain="[('model_id','=',model_id),('ttype','=','many2one'),('store','=',True)]",
        help="Laissez vide pour un champ direct du modèle de base.",
    )
    dim2_related_model_id = fields.Many2one(
        "ir.model",
        string="Dim 2 — Modèle lié",
        compute="_compute_dim2_related_model_id",
        store=True,
    )
    dim2_target_model_id = fields.Many2one(
        "ir.model",
        string="Dim 2 — Modèle effectif",
        compute="_compute_dim2_target_model_id",
    )
    dim2_group_field_id = fields.Many2one(
        "ir.model.fields",
        string="Dim 2 — Grouper par",
        ondelete="set null",
        domain="[('model_id','=',dim2_target_model_id),('store','=',True),"
               "('ttype','not in',['one2many','many2many','binary','html']),"
               "('name','!=','id')]",
    )
    dim2_time_granularity = fields.Selection(
        [
            ("day", "Jour"),
            ("week", "Semaine"),
            ("month", "Mois"),
            ("quarter", "Trimestre"),
            ("year", "Année"),
        ],
        string="Dim 2 — Granularité date",
    )

    @api.depends("dim1_link_field_id")
    def _compute_dim1_related_model_id(self):
        IrModel = self.env["ir.model"]
        for rec in self:
            rel = rec.dim1_link_field_id.relation if rec.dim1_link_field_id else False
            rec.dim1_related_model_id = IrModel.search([("model", "=", rel)], limit=1) if rel else False

    @api.depends("dim2_link_field_id")
    def _compute_dim2_related_model_id(self):
        IrModel = self.env["ir.model"]
        for rec in self:
            rel = rec.dim2_link_field_id.relation if rec.dim2_link_field_id else False
            rec.dim2_related_model_id = IrModel.search([("model", "=", rel)], limit=1) if rel else False

    @api.depends("dim2_link_field_id", "dim2_related_model_id", "model_id")
    def _compute_dim2_target_model_id(self):
        for rec in self:
            rec.dim2_target_model_id = rec.dim2_related_model_id if rec.dim2_link_field_id else rec.model_id

    def _auto_init(self):
        res = super()._auto_init()
        # Existing rows with tile_group_mode = NULL cause a validation error in the
        # selection_badge widget (Odoo 18) even without required=True.  Fill them once.
        self.env.cr.execute(
            "UPDATE dashboard_chart SET tile_group_mode = 'single' WHERE tile_group_mode IS NULL"
        )
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Override method to filter chars for dashboard email
        """
        args = list(args or [])
        context = dict(self.env.context)
        if context.get("is_automated"):
            domain = [("chart_type", "in", ["kpi", "tile", "list", "to_do"])]
            args = expression.AND([domain, args])
        return super(DashboardChart, self).name_search(
            name=name, args=args, operator=operator, limit=limit
        )

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        domain = list(domain or [])
        context = dict(self.env.context)
        if context.get("is_automated"):
            args = [("chart_type", "in", ["kpi", "tile", "list", "to_do"])]
            domain = expression.AND([args, domain])
        return super(DashboardChart, self).search_fetch(
            domain=domain,
            field_names=field_names,
            offset=offset,
            limit=limit,
            order=order,
        )

    @api.constrains("limit_record")
    def _check_limit_record(self):
        for chart in self:
            if chart.limit_record and chart.limit_record < 0:
                raise ValidationError(
                    _(
                        "Oops! The record limit can’t be less than zero. Please enter a value of zero or higher to continue."
                    )
                )

    @api.onchange("include_periods", "same_period_previous_years")
    def onchange_periods(self):
        if self.include_periods < 0:
            self.include_periods = 0
        if self.same_period_previous_years < 0:
            self.same_period_previous_years = 0

    @api.onchange("todo_layout")
    def onchange_todo_layout(self):
        """
        Set model as a False base on ToDo layout
        """
        if self.todo_layout == "default":
            self.model_id = False

    @api.onchange("date_filter_option")
    def onchange_date_filter_option(self):
        """
        Set periods
        """
        if self.date_filter_option in [
            "none",
            "past_till_now",
            "past_excluding_today",
            "future_starting_today",
            "future_starting_now",
            "future_starting_tomorrow",
        ]:
            self.include_periods = 0
            self.same_period_previous_years = 0

    @api.onchange("model_id")
    def onchange_model_id(self):
        """
        To set date filter field
        """
        self.measurement_field_ids = [(5,)]
        self.group_by_id = False
        self.measurement_field_id = False
        self.sub_group_by_id = False
        self.is_apply_multiplier = False
        self.map_group_by_id = False
        self.domain = "[]"
        self.date_filter_field_id = False
        self.sort_field_id = False
        self.list_field_ids = False
        self.item_view_action_ids = [(5,)]
        self.item_action_id = False
        self.list_measure_ids = False
        self.dim1_link_field_id = False
        self.dim1_group_field_id = False
        self.enable_dim2 = False
        self.dim2_link_field_id = False
        self.dim2_group_field_id = False
        self.dim2_time_granularity = False
        self.tile_group_by_id = False
        if self.model_id:
            field_id = (
                self.env["ir.model.fields"]
                .sudo()
                .search(
                    [("name", "=", "create_date"), ("model_id", "=", self.model_id.id)]
                )
            )
            self.date_filter_field_id = field_id.id
        self.onchange_apply_multiplier()

    @api.onchange("kpi_model_id")
    def onchange_kpi_model_id(self):
        """
        To set KPI date filter field
        """
        self.kpi_measurement_field_id = False
        self.kpi_data_type = "count"
        self.kpi_domain = "[]"
        self.kpi_comparison_type = "none"
        self.kpi_date_filter_option = "none"
        self.kpi_date_filter_field_id = False
        if self.kpi_model_id:
            field_id = (
                self.env["ir.model.fields"]
                .sudo()
                .search(
                    [
                        ("name", "=", "create_date"),
                        ("model_id", "=", self.kpi_model_id.id),
                    ]
                )
            )
            self.kpi_date_filter_field_id = field_id.id
        self.onchange_apply_multiplier()

    @api.onchange("measurement_field_id", "measurement_field_ids")
    def onchange_measurement_field(self):
        self.onchange_apply_multiplier()

    @api.onchange("is_apply_multiplier")
    def onchange_apply_multiplier(self):
        """
        Set chart multipliers
        """
        multiplier_list = [(5,)]
        if self.is_apply_multiplier:
            for measurement in self.measurement_field_ids:
                multiplier_list.append((0, 0, {"field_id": measurement.id}))
            if self.measurement_field_id:
                multiplier_list.append(
                    (0, 0, {"field_id": self.measurement_field_id.id})
                )
        self.chart_multiplier_ids = multiplier_list

    @api.onchange("chart_type")
    def onchange_chart_type(self):
        """
        Change model
        """
        # self.model_id = False
        self.background_color = "#fff"
        # self.onchange_model_id()
        chart_properties = {
            "tile": [
                "data_type",
                "measurement_field_id",
                "domain",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
                "tile_group_by_id",
                "tile_group_mode",
                "tile_group_limit",
            ],
            "kpi": [
                "data_type",
                "measurement_field_id",
                "domain",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "kpi_model_id",
                "kpi_data_type",
                "kpi_measurement_field_id",
                "kpi_limit_record",
                "kpi_comparison_type",
                "kpi_domain",
                "kpi_enable_target",
                "kpi_target_value",
                "kpi_view_type",
                "kpi_date_filter_field_id",
                "kpi_date_filter_option",
                "include_periods",
                "same_period_previous_years",
                "previous_period_comparision",
                "previous_period_type",
            ],
            "bar_chart": [
                "data_type",
                "measurement_field_id",
                "measurement_field_ids",
                "group_by_id",
                "time_range",
                "sub_group_by_id",
                "sub_time_range",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
                "dim1_link_field_id",
                "dim1_group_field_id",
                "enable_dim2",
                "dim2_link_field_id",
                "dim2_group_field_id",
                "dim2_time_granularity",
            ],
            "funnel_chart": [
                "data_type",
                "measurement_field_id",
                "group_by_id",
                "time_range",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "pyramid_chart": [
                "data_type",
                "measurement_field_id",
                "group_by_id",
                "time_range",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "map_chart": [
                "data_type",
                "measurement_field_id",
                "map_group_by_id",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "meter_chart": [
                "data_type",
                "measurement_field_id",
                "meter_target",
                "domain",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
                "previous_period_comparision",
                "previous_period_type",
            ],
            "to_do": [
                "todo_layout",
                "todo_action_ids",
                "domain",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
            ],
            "list": [
                "list_type",
                "list_field_ids",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
        }

        if self.chart_type in [
            "bar_chart",
            "column_chart",
            "doughnut_chart",
            "area_chart",
            "line_chart",
            "stackedcolumn_chart",
            "radial_chart",
            "scatter_chart",
        ]:
            chart_type = "bar_chart"
        elif self.chart_type in [
            "funnel_chart",
            "pyramid_chart",
            "pie_chart",
            "radar_chart",
        ]:
            chart_type = "funnel_chart"
        else:
            chart_type = self.chart_type

        allowed_fields = set(chart_properties.get(chart_type or "", []))
        all_fields = set(
            field for fields in chart_properties.values() for field in fields
        )

        for field in all_fields:
            if field not in allowed_fields:
                try:
                    if field in [
                        "measurement_field_ids",
                        "todo_action_ids",
                        "list_field_ids",
                    ]:
                        setattr(self, field, [(5,)])
                    elif field in ["domain", "kpi_domain"]:
                        setattr(self, field, "[]")
                    elif field in ["kpi_date_filter_option", "date_filter_option"]:
                        setattr(self, field, "none")
                    else:
                        setattr(self, field, False)
                except Exception:
                    _logger.info("pass")
        if self.chart_type == "to_do":
            self.todo_layout = "default"
        elif self.chart_type == "list":
            self.list_type = "standard"
        else:
            self.todo_layout = False
            self.list_type = False
            if not self.data_type:
                self.data_type = "count"

    def export_csv(self, name, chart_type, print_vals=False):
        """
        Export data in CSV file type for charts
        """
        print_options = False
        if print_vals.get("breadcrump_ids"):
            print_options = {
                "breadcrump_ids": print_vals.get("breadcrump_ids")[-1:],
                "domain": print_vals.get("prev_domains"),
            }
        data = self.get_chart_data(chart_type, name, print_options=print_options)
        if isinstance(data, dict) and data.get("type") == "error":
            return {"error": True}
        output = io.StringIO()
        writer = csv.writer(output)
        if chart_type in [
            "area_chart",
            "bar_chart",
            "column_chart",
            "doughnut_chart",
            "line_chart",
            "stackedcolumn_chart",
            "radial_chart",
            "scatter_chart",
        ]:
            all_metrics = set()
            normalized_rows = []

            for entry in data:
                category = entry.get("category")
                group_data = defaultdict(dict)
                for key, value in entry.items():
                    if key in ["category", "record_id"]:
                        continue
                    if " - " in key:
                        group_name, metric = key.rsplit(" - ", 1)
                    else:
                        group_name = key
                        metric = "Value"
                    group_data[group_name][metric] = value
                    all_metrics.add(metric)
                normalized_rows.extend(
                    [
                        {"Category": category, "Name": group_name, **metrics}
                        for group_name, metrics in group_data.items()
                    ]
                )
            metric_list = sorted(all_metrics)

            writer = csv.DictWriter(
                output, fieldnames=["Category", "Name"] + metric_list
            )
            writer.writeheader()
            for row in normalized_rows:
                writer.writerow(row)
        elif chart_type in [
            "funnel_chart",
            "pyramid_chart",
            "pie_chart",
            "radar_chart",
            "map_chart",
        ]:
            if chart_type == "map_chart":
                writer.writerow(["Name", "Value"])  # Header
            else:
                writer.writerow(["Category", "Value"])  # Header
            for row in data:
                if chart_type == "map_chart":
                    writer.writerow([row["name"], row["value"]])
                else:
                    writer.writerow([row["category"], row["value"]])
        elif chart_type == "list":
            column_lists = list(map(lambda col: col.get("name"), data["columns"]))
            writer.writerow(column_lists)
            for record in data["records"]:
                row_list = []
                for col in data["columns"]:
                    row_list.append(record.get(col["column_name"]))
                writer.writerow(row_list)

        elif chart_type == "to_do":
            if self.todo_layout == "default":
                writer.writerow(["Name", "Task"])
                for record in data["records"]:
                    for action in record.get("action_line_ids"):
                        if action.get("active_record"):
                            writer.writerow([record.get("name"), action.get("name")])
            else:
                writer.writerow(["Date", "Summary", "Name", "User", "Activity Type"])

                for record in data["records"]:
                    writer.writerow(
                        [
                            record["date"].strftime("%Y-%m-%d"),
                            record["summary"] if record["summary"] else "",
                            record["name"],
                            record["username"],
                            record["activity_type"],
                        ]
                    )

        file_name = name + ".csv"
        csv_bytes = output.getvalue().encode("utf-8")
        base64_content = base64.b64encode(csv_bytes).decode("utf-8")
        return {"file_content": base64_content, "file_name": file_name}

    def export_excel(self, name, chart_type, print_vals=False):
        """
        Export data in Excel file type for charts
        """

        def set_column_widths(worksheet, col_widths):
            """
            Set width of the column
            """
            for col, width in col_widths.items():
                worksheet.set_column(col, col, width + 2)

        def write_headers(worksheet, row, col, headers, header_format):
            """
            Set header values
            """
            for i, header in enumerate(headers):
                worksheet.write(row, col + i, header, header_format)

        def write_data_block(
            worksheet,
            start_row,
            start_col,
            base_keys,
            labels,
            category,
            header_fmt,
            cell_fmt,
        ):
            """
            Set date into blocks
            """
            worksheet.merge_range(
                start_row,
                start_col,
                start_row,
                start_col + len(labels),
                category,
                header_fmt,
            )
            worksheet.write(start_row + 1, start_col, "Name", cell_fmt)
            for j, label in enumerate(labels):
                worksheet.write(start_row + 1, start_col + 1 + j, label, cell_fmt)
            for i, (base, metrics) in enumerate(base_keys.items()):
                row = start_row + 2 + i
                worksheet.write(row, start_col, base, cell_fmt)
                for j, label in enumerate(labels):
                    worksheet.write(
                        row, start_col + 1 + j, metrics.get(label, ""), cell_fmt
                    )

        def get_max_col_widths(data, labels, base_keys, start_col):
            """
            Calculate column width
            """
            col_widths = {}
            col_widths[start_col] = max(len(k) for k in base_keys.keys())
            for j, label in enumerate(labels):
                col = start_col + 1 + j
                col_widths[col] = len(label)
                for metrics in base_keys.values():
                    col_widths[col] = max(
                        col_widths[col], len(str(metrics.get(label, "")))
                    )
            return col_widths

        print_options = False
        if print_vals.get("breadcrump_ids"):
            print_options = {
                "breadcrump_ids": print_vals.get("breadcrump_ids")[-1:],
                "domain": print_vals.get("prev_domains"),
            }
        data = self.get_chart_data(chart_type, name, print_options=print_options)
        if isinstance(data, dict) and data.get("type") == "error":
            return {"error": True}
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet(name)

        blocks_per_row, col_gap, row_gap = 3, 3, 3
        col_widths = {}

        if chart_type in {
            "area_chart",
            "bar_chart",
            "column_chart",
            "doughnut_chart",
            "line_chart",
            "stackedcolumn_chart",
            "radial_chart",
            "scatter_chart",
        }:
            for index, entry in enumerate(data):
                category = entry.get("category")
                base_keys = {}
                for key, value in entry.items():
                    if key not in ["category", "record_id"]:
                        if " - " in key and len(key.split(" - ")) > 1:
                            base, label = key.rsplit(" - ", 1)
                            base_keys.setdefault(base, {})[label] = value
                        else:
                            base_keys.setdefault("Count", {})[key] = value
                if not base_keys:
                    continue
                labels = sorted(
                    {label for metrics in base_keys.values() for label in metrics}
                )
                block_x = (index % blocks_per_row) * (len(labels) + 1 + col_gap)
                block_y = (index // blocks_per_row) * (len(base_keys) + 2 + row_gap)
                write_data_block(
                    worksheet,
                    block_y,
                    block_x,
                    base_keys,
                    labels,
                    category,
                    workbook.add_format(
                        {
                            "bold": True,
                            "align": "center",
                            "valign": "vcenter",
                            "border": 1,
                            "bg_color": "#D9E1F2",
                        }
                    ),
                    workbook.add_format({"bold": True, "border": 1}),
                )
                col_widths.update(get_max_col_widths(data, labels, base_keys, block_x))
            set_column_widths(worksheet, col_widths)

        elif chart_type in {
            "funnel_chart",
            "pyramid_chart",
            "pie_chart",
            "radar_chart",
            "map_chart",
        }:
            for index, entry in enumerate(data):
                category = (
                    entry.get("category")
                    if chart_type != "map_chart"
                    else entry.get("name")
                )
                value = entry.get("value", "")
                block_x = (index % blocks_per_row) * (3 + col_gap)
                block_y = (index // blocks_per_row) * (3 + row_gap)

                worksheet.merge_range(
                    block_y,
                    block_x,
                    block_y,
                    block_x + 1,
                    category,
                    workbook.add_format(
                        {
                            "bold": True,
                            "align": "center",
                            "valign": "vcenter",
                            "border": 1,
                            "bg_color": "#F4B084",
                        }
                    ),
                )
                worksheet.write(
                    block_y + 1,
                    block_x,
                    "Value",
                    workbook.add_format({"bold": True, "border": 1}),
                )
                worksheet.write(
                    block_y + 1, block_x + 1, value, workbook.add_format({"border": 1})
                )
                col_widths[block_x] = max(
                    col_widths.get(block_x, 0), len(category) if category else 5
                )
                col_widths[block_x + 1] = max(
                    col_widths.get(block_x + 1, 0), len(str(value))
                )
            set_column_widths(worksheet, col_widths)

        elif chart_type == "list":
            columns = data["columns"]
            records = data["records"]

            column_order = [col["column_name"] for col in columns]
            column_headers = [col["name"] for col in columns]
            write_headers(
                worksheet,
                0,
                0,
                column_headers,
                workbook.add_format({"bold": True, "bg_color": "#BDD7EE", "border": 1}),
            )
            for row_idx, record in enumerate(records, start=1):
                for col_idx, key in enumerate(column_order):
                    worksheet.write(
                        row_idx,
                        col_idx,
                        record.get(key, ""),
                        workbook.add_format({"border": 1}),
                    )
            for col_idx, key in enumerate(column_order):
                max_width = max(len(str(record.get(key, ""))) for record in records)
                header_width = len(column_headers[col_idx])
                worksheet.set_column(col_idx, col_idx, max(max_width, header_width) + 2)

        elif chart_type == "to_do":
            if self.todo_layout == "default":
                records = data["records"]
                columns_data = {
                    record["name"]: [
                        line["name"]
                        for line in record.get("action_line_ids", [])
                        if line.get("active_record")
                    ]
                    for record in records
                }
                write_headers(
                    worksheet,
                    0,
                    0,
                    list(columns_data.keys()),
                    workbook.add_format(
                        {
                            "bold": True,
                            "bg_color": "#D9E1F2",
                            "border": 1,
                            "align": "center",
                        }
                    ),
                )
                for col_idx, (col_name, lines) in enumerate(columns_data.items()):
                    for row_idx, value in enumerate(lines, start=1):
                        worksheet.write(
                            row_idx, col_idx, value, workbook.add_format({"border": 1})
                        )
                    max_width = max([len(str(v)) for v in lines], default=0)
                    worksheet.set_column(
                        col_idx, col_idx, max(max_width, len(col_name)) + 2
                    )

            else:
                records = data.get("records", [])
                headers = ["Date", "Summary", "Name", "User", "Activity Type"]
                keys = ["date", "summary", "name", "username", "activity_type"]
                write_headers(
                    worksheet,
                    0,
                    0,
                    headers,
                    workbook.add_format(
                        {
                            "bold": True,
                            "bg_color": "#B7DEE8",
                            "border": 1,
                            "align": "center",
                        }
                    ),
                )
                date_fmt = workbook.add_format(
                    {"num_format": "dd-mm-yyyy", "border": 1}
                )
                text_fmt = workbook.add_format({"border": 1})
                for row_idx, record in enumerate(records, start=1):
                    for col_idx, key in enumerate(keys):
                        val = record.get(key, "")
                        if key == "date" and val:
                            worksheet.write_datetime(row_idx, col_idx, val, date_fmt)
                        else:
                            worksheet.write(
                                row_idx,
                                col_idx,
                                val if val is not False else "",
                                text_fmt,
                            )
                for col_idx, key in enumerate(keys):
                    max_width = max(len(str(record.get(key, ""))) for record in records)
                    worksheet.set_column(
                        col_idx, col_idx, max(max_width, len(headers[col_idx])) + 2
                    )

        workbook.close()
        output.seek(0)
        return {
            "file_content": base64.b64encode(output.read()).decode("utf-8"),
            "file_name": f"{name}.xlsx",
        }

    def evaluate_odoo_domain(self, domain_string):
        class OdooSafeDatetime:
            def __init__(self, dt):
                self._dt = dt

            def to_utc(self):
                if hasattr(self._dt, "replace") and self._dt.tzinfo is None:
                    # If datetime is naive, treat as UTC
                    utc_dt = self._dt
                else:
                    utc_dt = fields.Datetime.to_datetime(self._dt)
                return OdooSafeDatetime(utc_dt)

            def strftime(self, fmt):
                return self._dt.strftime(fmt)

        class OdooDatetimeClass:
            @staticmethod
            def combine(date_obj, time_obj):
                combined = datetime.combine(date_obj, time_obj)
                return OdooSafeDatetime(combined)

        class DatetimeModule:
            datetime = OdooDatetimeClass
            time = time

        def get_context_today():
            return fields.Datetime.context_timestamp(self, datetime.now()).date()

        eval_context = {
            "datetime": DatetimeModule(),
            "context_today": get_context_today,
            "relativedelta": relativedelta,
        }

        try:
            return safe_eval(domain_string, eval_context)
        except Exception as e:
            _logger.warning(f"Failed to evaluate domain: {domain_string}, Error: {e}")
            return []

    def _count_distinct_sql(self, record_obj, domain, group_field=None, distinct_field=None, limit=None):
        """
        COUNT(DISTINCT distinct_field) GROUP BY group_field via SQL.
        Utilise ORM search() pour appliquer le domaine + droits d'accès, puis SQL pour l'agrégation.

        Retourne:
        - Si group_field fourni : liste de (group_raw_val, count_int) triée par count desc
        - Sinon : un entier (count global distinct)
        """
        records = record_obj.with_context(group_by=None).search(domain)
        if not records:
            return [] if group_field else 0
        table = record_obj._table
        df_col = distinct_field or 'id'
        limit_clause = f"LIMIT {limit}" if limit else ""
        if group_field:
            self.env.cr.execute(
                f"SELECT {group_field}, COUNT(DISTINCT {df_col}) AS cnt "
                f"FROM {table} WHERE id IN %s GROUP BY {group_field} ORDER BY cnt DESC {limit_clause}",
                (tuple(records.ids),),
            )
            return self.env.cr.fetchall()
        else:
            self.env.cr.execute(
                f"SELECT COUNT(DISTINCT {df_col}) FROM {table} WHERE id IN %s",
                (tuple(records.ids),),
            )
            row = self.env.cr.fetchone()
            return row[0] if row else 0

    def _format_date_granularity(self, val, granularity):
        """Format a date/datetime value according to a time granularity string."""
        from datetime import datetime
        if not val:
            return 'N/A'
        if isinstance(val, str):
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    val = datetime.strptime(val, fmt)
                    break
                except ValueError:
                    pass
            else:
                return str(val)
        fmt_map = {
            'day': '%Y-%m-%d',
            'week': lambda d: f"{d.year}-W{d.strftime('%W')}",
            'month': '%Y-%m',
            'quarter': lambda d: f"{d.year}-Q{(d.month - 1) // 3 + 1}",
            'year': '%Y',
        }
        fmt = fmt_map.get(granularity, '%Y-%m')
        return fmt(val) if callable(fmt) else val.strftime(fmt)

    def _get_multidim_data_sql(self, conf_obj, record_ids):
        """
        Execute a 2-dimension SQL aggregation.

        Dim 1 : champ d'un modèle lié (via dim1_link_col → dim1_related_table)
                Si dim1_group_field est lui-même un Many2one, un 2e JOIN récupère son libellé.
        Dim 2 : champ direct OU champ d'un 2e modèle lié (dim2_link_field → dim2_related_table)
                Granularité date optionnelle (dim2_time_granularity).

        Retourne : liste de dicts [{dim1: str, dim2: str|None, measure_val: float}]
        """
        if not record_ids:
            return []

        base_table = self.env[conf_obj.model]._table

        # ── Dim 1 ──────────────────────────────────────────────────────────────
        joins = [
            f"LEFT JOIN {conf_obj.dim1_related_table} dim1_rel"
            f" ON {base_table}.{conf_obj.dim1_link_col} = dim1_rel.id"
        ]

        if conf_obj.dim1_group_field_ttype == "many2one" and conf_obj.dim1_group_field_relation:
            dim1_target_model = self.env[conf_obj.dim1_group_field_relation]
            dim1_target_table = dim1_target_model._table
            dim1_name_col = dim1_target_model._rec_name or "name"
            joins.append(
                f"LEFT JOIN {dim1_target_table} dim1_target"
                f" ON dim1_rel.{conf_obj.dim1_group_field} = dim1_target.id"
            )
            dim1_select = f"COALESCE(dim1_target.{dim1_name_col}::TEXT, 'N/A') AS dim1"
            dim1_group_expr = f"dim1_target.{dim1_name_col}"
        else:
            dim1_select = f"COALESCE(dim1_rel.{conf_obj.dim1_group_field}::TEXT, 'N/A') AS dim1"
            dim1_group_expr = f"dim1_rel.{conf_obj.dim1_group_field}"

        selects = [dim1_select]
        group_exprs = [dim1_group_expr]

        # ── Dim 2 ──────────────────────────────────────────────────────────────
        if conf_obj.enable_dim2 and conf_obj.dim2_group_field:
            if conf_obj.dim2_link_field and conf_obj.dim2_related_table:
                joins.append(
                    f"LEFT JOIN {conf_obj.dim2_related_table} dim2_rel"
                    f" ON {base_table}.{conf_obj.dim2_link_field} = dim2_rel.id"
                )
                if conf_obj.dim2_group_field_ttype == "many2one" and conf_obj.dim2_group_field_relation:
                    dim2_target_model = self.env[conf_obj.dim2_group_field_relation]
                    dim2_target_table = dim2_target_model._table
                    dim2_name_col = dim2_target_model._rec_name or "name"
                    joins.append(
                        f"LEFT JOIN {dim2_target_table} dim2_target"
                        f" ON dim2_rel.{conf_obj.dim2_group_field} = dim2_target.id"
                    )
                    dim2_raw_expr = f"dim2_target.{dim2_name_col}"
                else:
                    dim2_raw_expr = f"dim2_rel.{conf_obj.dim2_group_field}"
            else:
                dim2_raw_expr = f"{base_table}.{conf_obj.dim2_group_field}"

            if conf_obj.dim2_time_granularity:
                gran = conf_obj.dim2_time_granularity
                fmt = {"day": "YYYY-MM-DD", "week": "IYYY-IW", "month": "YYYY-MM",
                       "quarter": "YYYY-\"Q\"Q", "year": "YYYY"}.get(gran, "YYYY-MM")
                selects.append(
                    f"TO_CHAR(DATE_TRUNC('{gran}', {dim2_raw_expr}::TIMESTAMP), '{fmt}') AS dim2"
                )
                group_exprs.append(f"DATE_TRUNC('{gran}', {dim2_raw_expr}::TIMESTAMP)")
            else:
                selects.append(f"COALESCE({dim2_raw_expr}::TEXT, 'N/A') AS dim2")
                group_exprs.append(dim2_raw_expr)

        # ── Mesure ─────────────────────────────────────────────────────────────
        if conf_obj.data_type == "count":
            selects.append("COUNT(*) AS measure_val")
        elif conf_obj.data_type in ("sum", "average") and conf_obj.measurement_field_id:
            m_col = f"{base_table}.{conf_obj.measurement_field_id.name}"
            agg = "SUM" if conf_obj.data_type == "sum" else "AVG"
            selects.append(f"COALESCE({agg}({m_col}), 0) AS measure_val")
        else:
            selects.append("COUNT(*) AS measure_val")

        limit_clause = f"LIMIT {conf_obj.limit_record}" if conf_obj.limit_record else ""
        group_clause = ", ".join(group_exprs)
        join_clause = "\n        ".join(joins)

        query = f"""
            SELECT {', '.join(selects)}
            FROM {base_table}
            {join_clause}
            WHERE {base_table}.id IN %s
            GROUP BY {group_clause}
            ORDER BY {group_clause}
            {limit_clause}
        """
        self.env.cr.execute(query, (tuple(record_ids),))
        return self.env.cr.dictfetchall()

    def _format_multidim_prepared_data(self, rows, conf_obj):
        """
        Pivote les lignes SQL en format compatible AmCharts grouped bar/column.

        Mode 1D (enable_dim2 désactivé) :
            [{"category": dim1_val, " - Measure": val}, ...]

        Mode 2D :
            [{"category": dim2_val, " - dim1_A": val, " - dim1_B": val, ...}, ...]
            + liste des clés de séries
        """
        if conf_obj.measurement_field_id:
            measure_label = conf_obj.measurement_field_id.field_description or "Valeur"
        else:
            measure_label = "Nombre"

        if not conf_obj.enable_dim2 or not conf_obj.dim2_group_field:
            prepared = [
                {
                    "category": str(row.get("dim1") or "N/A"),
                    f" - {measure_label}": float(row.get("measure_val") or 0),
                }
                for row in rows
            ]
            return prepared, [f" - {measure_label}"]

        # 2D pivot : dim2 → catégories X, dim1 → séries
        from collections import OrderedDict
        categories_ordered = OrderedDict()
        series_keys = []

        for row in rows:
            cat = str(row.get("dim2") or "N/A")
            serie = f" - {str(row.get('dim1') or 'N/A')}"
            val = float(row.get("measure_val") or 0)

            if cat not in categories_ordered:
                categories_ordered[cat] = {"category": cat}
            categories_ordered[cat][serie] = val

            if serie not in series_keys:
                series_keys.append(serie)

        return list(categories_ordered.values()), series_keys

    def _get_multidim_count_distinct(self, conf_obj, domain, record_obj):
        """
        Chemin COUNT(DISTINCT) pour le multi-dim.
        SQL : GROUP BY dim1_link_field [, dim2_key] + COUNT(DISTINCT measurement_field).
        Résolution des labels via browse() sur les modèles liés.
        """
        dim2_groupby_key = None
        if conf_obj.enable_dim2 and conf_obj.dim2_group_field:
            dim2_groupby_key = conf_obj.dim2_link_field if conf_obj.dim2_link_field else conf_obj.dim2_group_field

        rec_ids = record_obj.search(domain).ids
        if not rec_ids:
            return {"type": "error", "message": "No Data to display!"}

        table = record_obj._table
        lf_col = conf_obj.dim1_link_field
        df_col = conf_obj.measurement_field_id.name
        gf_cols = [lf_col] + ([dim2_groupby_key] if dim2_groupby_key else [])
        gc = ", ".join(f"{table}.{c}" for c in gf_cols)
        sc = ", ".join(f"{table}.{c}" for c in gf_cols)
        self.env.cr.execute(
            f"SELECT {sc}, COUNT(DISTINCT {table}.{df_col}) AS cnt "
            f"FROM {table} WHERE {table}.id IN %s GROUP BY {gc}",
            (tuple(rec_ids),),
        )
        sql_rows = self.env.cr.fetchall()
        if not sql_rows:
            return {"type": "error", "message": "No Data to display!"}

        # Résoudre dim1 labels
        link_ids = list({row[0] for row in sql_rows if row[0]})
        id_to_dim1_label = {}
        for rec in self.env[conf_obj.dim1_related_model].sudo().browse(link_ids):
            try:
                gf_val = rec[conf_obj.dim1_group_field]
            except Exception:
                gf_val = False
            if hasattr(gf_val, 'display_name'):
                label = gf_val.display_name or 'N/A'
            elif gf_val is not False and gf_val is not None and gf_val != '':
                if conf_obj.dim1_group_field_ttype == 'selection':
                    fld = self.env[conf_obj.dim1_related_model]._fields.get(conf_obj.dim1_group_field)
                    sel = dict(fld.selection or []) if fld else {}
                    label = sel.get(gf_val, str(gf_val))
                else:
                    label = str(gf_val)
            else:
                label = 'N/A'
            id_to_dim1_label[rec.id] = label

        # Résoudre dim2 labels si via modèle lié
        dim2_id_to_label = {}
        dim2_related_model = getattr(conf_obj, 'dim2_related_model', None)
        if dim2_groupby_key and conf_obj.dim2_link_field and dim2_related_model:
            d2_ids = list({row[1] for row in sql_rows if len(row) > 2 and row[1]})
            for rec in self.env[dim2_related_model].sudo().browse(d2_ids):
                try:
                    d2_val = rec[conf_obj.dim2_group_field]
                except Exception:
                    d2_val = False
                if hasattr(d2_val, 'display_name'):
                    lbl = d2_val.display_name or 'N/A'
                elif d2_val is not False and d2_val is not None:
                    lbl = self._format_date_granularity(d2_val, conf_obj.dim2_time_granularity) if conf_obj.dim2_time_granularity else str(d2_val)
                else:
                    lbl = 'N/A'
                dim2_id_to_label[rec.id] = lbl

        # Pivot
        mf_label = conf_obj.measurement_field_id.field_description if conf_obj.measurement_field_id else "Nb distinct"
        pivot = {}
        dim1_order = []
        dim2_order = []
        for row in sql_rows:
            lid = row[0]
            dim1_label = id_to_dim1_label.get(lid, 'N/A') if lid else 'N/A'
            if dim2_groupby_key:
                dv = row[1]
                if conf_obj.dim2_link_field and dim2_related_model:
                    dim2_label = dim2_id_to_label.get(dv, 'N/A') if dv else 'N/A'
                elif dv is not None and dv is not False:
                    dim2_label = self._format_date_granularity(str(dv), conf_obj.dim2_time_granularity) if conf_obj.dim2_time_granularity else str(dv)
                else:
                    dim2_label = 'N/A'
            else:
                dim2_label = None
            measure = float(row[-1] or 0)
            if dim1_label not in pivot:
                pivot[dim1_label] = {}
                dim1_order.append(dim1_label)
            if dim2_label not in dim2_order:
                dim2_order.append(dim2_label)
            pivot[dim1_label][dim2_label] = pivot[dim1_label].get(dim2_label, 0.0) + measure

        if conf_obj.limit_record:
            if not conf_obj.enable_dim2 or not dim2_groupby_key:
                dim1_order = dim1_order[:conf_obj.limit_record]
            else:
                dim2_order = dim2_order[:conf_obj.limit_record]

        if not conf_obj.enable_dim2 or not dim2_groupby_key:
            return [{"category": lbl, f" - {mf_label}": pivot[lbl].get(None, 0.0)} for lbl in dim1_order]
        result = []
        for d2 in dim2_order:
            row = {"category": d2}
            for d1 in dim1_order:
                row[f" - {d1}"] = pivot.get(d1, {}).get(d2, 0.0)
            result.append(row)
        return result

    def get_multidim_chart_data(self, conf_obj):
        """
        Multi-dim groupby — paradigme ORM natif (sans SQL direct).

        Étape 1 : read_group(lazy=False, groupby=[dim1_link_field, dim2_key?]) sur le modèle
                  principal avec with_context(group_by=None) pour neutraliser tout group_by
                  natif du context Odoo.
        Étape 2 : Résoudre dim1_link_id → dim1_group_label via browse() sur le modèle lié.
                  Tous les champs du modèle lié (ex: res.partner) sont accessibles directement.
        Étape 3 : Pivot Python (dim1_label, dim2_label?) → mesure → format AmCharts.
        """
        if not conf_obj.model:
            return {"type": "error", "message": "Please Select Model!"}
        if not conf_obj.dim1_link_field or not conf_obj.dim1_group_field:
            return {"type": "error", "message": "Configurez la Dimension 1 (liaison + champ de regroupement)."}
        if conf_obj.data_type not in ("count",) and not conf_obj.measurement_field_id:
            return {"type": "error", "message": "Sélectionnez un champ de mesure (Measure Field)."}

        # ── Domaine ─────────────────────────────────────────────────────────
        record_obj = self.env[conf_obj.model].with_context(group_by=None)
        domain = list(conf_obj.domain)
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            not getattr(conf_obj, "use_global_date", False)
            and conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                domain.extend(date_domain["domain"])

        # ── count_distinct : SQL direct (read_group ne supporte pas COUNT DISTINCT) ──
        if conf_obj.data_type == "count_distinct":
            return self._get_multidim_count_distinct(conf_obj, domain, record_obj)

        # ── Groupby : dim1_link_field direct + dim2 optionnel ───────────────
        # On groupe par le champ de liaison (ex: partner_id) sur le modèle principal.
        # La résolution dim1_link → dim1_group_label se fait ensuite via browse().
        groupby_list = [conf_obj.dim1_link_field]

        dim2_groupby_key = None
        if conf_obj.enable_dim2 and conf_obj.dim2_group_field:
            dim2_groupby_key = conf_obj.dim2_link_field if conf_obj.dim2_link_field else conf_obj.dim2_group_field
            groupby_list.append(dim2_groupby_key)

        if conf_obj.data_type == "count":
            fields_list = list(groupby_list)
        else:
            mf_name = conf_obj.measurement_field_id.name
            agg = "sum" if conf_obj.data_type == "sum" else "avg"
            fields_list = list(groupby_list) + [f"{mf_name}:{agg}"]

        # ── read_group avec lazy=False ───────────────────────────────────────
        raw_groups = record_obj.read_group(
            domain=domain,
            fields=fields_list,
            groupby=groupby_list,
            lazy=False,
        )
        if not raw_groups:
            return {"type": "error", "message": "No Data to display!"}

        # ── Résoudre dim1 : link_ids → group_field_labels ───────────────────
        # Appel ORM sur le modèle lié (ex: res.partner) : tous ses champs disponibles
        link_ids = []
        for g in raw_groups:
            val = g.get(conf_obj.dim1_link_field)
            lid = val[0] if isinstance(val, (list, tuple)) else val
            if lid and lid not in link_ids:
                link_ids.append(lid)

        related_model_obj = self.env[conf_obj.dim1_related_model].sudo()
        id_to_dim1_label = {}
        for rec in related_model_obj.browse(link_ids):
            try:
                gf_val = rec[conf_obj.dim1_group_field]
            except Exception:
                gf_val = False
            if hasattr(gf_val, 'display_name'):
                label = gf_val.display_name or 'N/A'
            elif gf_val is not False and gf_val is not None and gf_val != '':
                if conf_obj.dim1_group_field_ttype == 'selection':
                    fld = related_model_obj._fields.get(conf_obj.dim1_group_field)
                    sel = dict(fld.selection or []) if fld else {}
                    label = sel.get(gf_val, str(gf_val))
                else:
                    label = str(gf_val)
            else:
                label = 'N/A'
            id_to_dim1_label[rec.id] = label

        # ── Résoudre dim2 si elle passe par un modèle lié ──────────────────
        dim2_id_to_label = {}
        dim2_related_model = getattr(conf_obj, 'dim2_related_model', None)
        if conf_obj.enable_dim2 and conf_obj.dim2_link_field and dim2_related_model:
            d2_ids = []
            for g in raw_groups:
                val = g.get(dim2_groupby_key)
                did = val[0] if isinstance(val, (list, tuple)) else val
                if did and did not in d2_ids:
                    d2_ids.append(did)
            d2_model_obj = self.env[dim2_related_model].sudo()
            for rec in d2_model_obj.browse(d2_ids):
                try:
                    d2_val = rec[conf_obj.dim2_group_field]
                except Exception:
                    d2_val = False
                if hasattr(d2_val, 'display_name'):
                    lbl = d2_val.display_name or 'N/A'
                elif d2_val is not False and d2_val is not None:
                    lbl = self._format_date_granularity(d2_val, conf_obj.dim2_time_granularity) if conf_obj.dim2_time_granularity else str(d2_val)
                else:
                    lbl = 'N/A'
                dim2_id_to_label[rec.id] = lbl

        # ── Pivot Python ────────────────────────────────────────────────────
        mf_name_key = conf_obj.measurement_field_id.name if conf_obj.measurement_field_id else None
        mf_label = conf_obj.measurement_field_id.field_description if conf_obj.measurement_field_id else "Nombre"

        pivot = {}       # {dim1_label: {dim2_label_or_None: float}}
        dim1_order = []
        dim2_order = []

        for g in raw_groups:
            # Dim1 label
            lv = g.get(conf_obj.dim1_link_field)
            lid = lv[0] if isinstance(lv, (list, tuple)) else lv
            dim1_label = id_to_dim1_label.get(lid, 'N/A') if lid else 'N/A'

            # Dim2 label
            if conf_obj.enable_dim2 and dim2_groupby_key:
                dv = g.get(dim2_groupby_key)
                if conf_obj.dim2_link_field and dim2_related_model:
                    did = dv[0] if isinstance(dv, (list, tuple)) else dv
                    dim2_label = dim2_id_to_label.get(did, 'N/A') if did else 'N/A'
                elif isinstance(dv, (list, tuple)):
                    dim2_label = str(dv[1]) if len(dv) > 1 and dv[1] else 'N/A'
                elif dv is not None and dv is not False:
                    dim2_label = self._format_date_granularity(dv, conf_obj.dim2_time_granularity) if conf_obj.dim2_time_granularity else str(dv)
                else:
                    dim2_label = 'N/A'
            else:
                dim2_label = None

            # Mesure
            measure = float(g.get("__count", 0) or 0) if conf_obj.data_type == "count" else float(g.get(mf_name_key, 0) or 0)

            if dim1_label not in pivot:
                pivot[dim1_label] = {}
                dim1_order.append(dim1_label)
            if dim2_label not in dim2_order:
                dim2_order.append(dim2_label)
            pivot[dim1_label][dim2_label] = pivot[dim1_label].get(dim2_label, 0.0) + measure

        # ── Limite ──────────────────────────────────────────────────────────
        if conf_obj.limit_record:
            if not conf_obj.enable_dim2 or dim2_groupby_key is None:
                dim1_order = dim1_order[:conf_obj.limit_record]
            else:
                dim2_order = dim2_order[:conf_obj.limit_record]

        # ── Format AmCharts ─────────────────────────────────────────────────
        if not conf_obj.enable_dim2 or dim2_groupby_key is None:
            # Mode 1D : category = dim1_group_label
            return [
                {"category": lbl, f" - {mf_label}": pivot[lbl].get(None, 0.0)}
                for lbl in dim1_order
            ]

        # Mode 2D : category = dim2_label, séries = dim1_group_labels
        result = []
        for d2 in dim2_order:
            row = {"category": d2}
            for d1 in dim1_order:
                row[f" - {d1}"] = pivot.get(d1, {}).get(d2, 0.0)
            result.append(row)
        return result

    def _get_nested_value(self, record, field_path):
        """Traverse a dotted field path on a record (kept for backward compat)."""
        parts = field_path.split(".")
        value = record
        for part in parts:
            if not value or isinstance(value, (bool, int, float, str)):
                return False
            value = getattr(value, part, False)
        return value

    def _resolve_partner_selection_label(self, base_model_name, dotted_path, val):
        """For 'partner_id.field_name', resolve a Selection key to its French label.
        Returns None if the field is not Selection or the key is not found."""
        if not val or not dotted_path or '.' not in dotted_path:
            return None
        try:
            parts = dotted_path.split('.')
            cur = self.env[base_model_name]
            for part in parts[:-1]:
                fld = cur._fields.get(part)
                if not fld or not getattr(fld, 'comodel_name', None):
                    return None
                cur = self.env[fld.comodel_name]
            last_fld = cur._fields.get(parts[-1])
            if not last_fld or last_fld.type != 'selection':
                return None
            sel = last_fld.selection
            if callable(sel):
                sel = sel(cur)
            elif isinstance(sel, str):
                sel = getattr(cur, sel, lambda: [])()
            return dict(sel or {}).get(val)
        except Exception:
            return None

    def _build_global_filter_domain(self, model_name, global_filters):
        """Translate the global filter panel values into an Odoo domain list."""
        if not global_filters or not model_name:
            return []
        try:
            model_obj = self.env[model_name]
        except KeyError:
            return []
        model_fields = model_obj._fields
        extra_domain = []

        # Direct partner selector: ('partner_id', '=', id)
        partner_id = global_filters.get("partner_id")
        if partner_id and "partner_id" in model_fields:
            extra_domain.append(("partner_id", "=", int(partner_id)))

        # Partner field filter: ('partner_id.field_name', operator, value)
        # Odoo ORM supports dotted notation in domain for Many2one traversal.
        # Many2many fields use 'in' with a list; all other types use '='.
        partner_field = global_filters.get("partner_field")
        partner_field_value = global_filters.get("partner_field_value")
        if (
            partner_field
            and partner_field_value not in (None, "", False)
            and "partner_id" in model_fields
        ):
            partner_field_obj = self.env["res.partner"]._fields.get(partner_field)
            if partner_field_obj and partner_field_obj.type == "many2many":
                # many2many: filter records whose partner has this value in the m2m
                extra_domain.append(
                    (f"partner_id.{partner_field}", "in", [int(partner_field_value)])
                )
            else:
                extra_domain.append(
                    (f"partner_id.{partner_field}", "=", partner_field_value)
                )

        # Invoice state filter (only meaningful on account.move)
        invoice_state = global_filters.get("invoice_state")
        if invoice_state and model_name == "account.move" and "state" in model_fields:
            extra_domain.append(("state", "=", invoice_state))

        # Global date range: use the chart's date_filter_field as date column
        date_from = global_filters.get("date_from")
        date_to = global_filters.get("date_to")
        if date_from and date_to and self.date_filter_field_id:
            field_name = self.date_filter_field_id.name
            if field_name in model_fields:
                extra_domain.extend(
                    [
                        (field_name, ">=", date_from),
                        (field_name, "<=", date_to),
                    ]
                )

        return extra_domain

    @api.model
    def get_partner_filter_fields(self):
        """Return exactly the res.partner fields exposed in the global filter panel."""
        # Exact list of (field_name, french_label) to expose in the filter panel.
        ALLOWED_FIELDS = [
            ("name",                "Nom Entreprise"),
            ("state_id",            "Province"),
            ("company_id",          "Société / Maison mère"),
            ("identifiant",         "Numéro d'identification"),
            ("legal_status_code",   "Statut juridique"),
            ("legal_status_detail", "Précision statut juridique"),
            ("categorie_cotisant",  "Catégorie de cotisant"),
            ("secteur",             "Secteur d'activité"),
        ]

        # Resolve RDC country ID once — more reliable than dotted domain notation
        rdc = self.env["res.country"].search([("code", "=", "CD")], limit=1)
        FIELD_DOMAINS = {
            "state_id": [["country_id", "=", rdc.id]] if rdc else [],
        }

        partner_model = self.env["res.partner"]
        fields_data = []
        for field_name, french_label in ALLOWED_FIELDS:
            try:
                field = partner_model._fields.get(field_name)
                if not field:
                    continue
                field_info = {
                    "name": field_name,
                    "label": french_label,
                    "type": field.type,
                }
                if field.type in ("many2one", "many2many"):
                    field_info["comodel"] = getattr(field, "comodel_name", "") or ""
                    if field_name in FIELD_DOMAINS:
                        field_info["domain"] = FIELD_DOMAINS[field_name]
                elif field.type == "selection":
                    sel = getattr(field, "selection", [])
                    if isinstance(sel, str):
                        method = getattr(partner_model, sel, None)
                        sel = method() if callable(method) else []
                    elif callable(sel):
                        sel = sel(partner_model)
                    field_info["selection"] = [
                        [item[0], item[1]]
                        for item in (sel or [])
                        if isinstance(item, (list, tuple)) and len(item) >= 2
                    ]
                fields_data.append(field_info)
            except Exception:
                continue

        # Preserve the order defined in ALLOWED_FIELD_NAMES (no sort)
        return fields_data

    def get_chart_data(
        self,
        chart_type,
        name,
        isDirty=False,
        data=False,
        extra_action=False,
        print_options=False,
        global_filters=None,
    ):
        """
        this function is called from chart wrapper and form preview.
        In case of any field get changed in form view then this function will
        make sure it will preview based on latest changes of configuration,
        also In case of there is item action and item views are linked to charts then in
        each click on chart this function will redirect action or replace current chart
        """
        conf, domain = self._init_configuration()

        # Apply global dashboard filters (session-level, from the filter panel)
        if global_filters:
            gf_domain = self._build_global_filter_domain(conf.model, global_filters)
            if gf_domain:
                conf.domain = conf.domain + gf_domain
                domain = conf.domain.copy()
            if global_filters.get("date_from") and global_filters.get("date_to"):
                conf.use_global_date = True
        if isDirty:
            self._handle_dirty_data(conf, data)
        conf.chart_type = chart_type
        if print_options:
            domain = print_options.get("domain")
            view_item = self.env["item.view.action"].browse(
                print_options.get("breadcrump_ids")
            )
            if view_item:
                chart_type = view_item.chart_type
                conf.domain = domain
                if not conf.measurement_field_id and conf.measurement_field_ids:
                    conf.measurement_field_id = conf.measurement_field_ids[0]
                if not conf.measurement_field_ids:
                    conf.measurement_field_ids = conf.measurement_field_id
                conf.group_by = view_item.group_by_id.name
                conf.sort_field = view_item.sort_field_id.name
                conf.sort_order = view_item.sort_order
                conf.limit_record = view_item.limit_record
        else:
            domain = self._process_domain(domain, extra_action, self.group_by_id)
            view_item = self._get_view_item(extra_action)
            if view_item:
                chart_type = view_item.chart_type
                conf.domain = domain
                if not conf.measurement_field_id and conf.measurement_field_ids:
                    conf.measurement_field_id = conf.measurement_field_ids[0]
                if not conf.measurement_field_ids:
                    conf.measurement_field_ids = conf.measurement_field_id
                conf.group_by = view_item.group_by_id.name
                conf.sort_field = view_item.sort_field_id.name
                conf.sort_order = view_item.sort_order
                conf.limit_record = view_item.limit_record
        # Charts compatibles avec le groupby multi-dimensionnel
        _multidim_compatible = {
            "area_chart", "bar_chart", "column_chart", "doughnut_chart",
            "line_chart", "stackedcolumn_chart", "radial_chart", "scatter_chart",
        }
        chart_handlers = {
            "area_chart": self.get_measurement_group_data,
            "bar_chart": self.get_measurement_group_data,
            "column_chart": self.get_measurement_group_data,
            "doughnut_chart": self.get_measurement_group_data,
            "line_chart": self.get_measurement_group_data,
            "stackedcolumn_chart": self.get_measurement_group_data,
            "radial_chart": self.get_measurement_group_data,
            "scatter_chart": self.get_measurement_group_data,
            "funnel_chart": self.get_category_value_data,
            "pyramid_chart": self.get_category_value_data,
            "pie_chart": self.get_category_value_data,
            "radar_chart": self.get_category_value_data,
            "map_chart": self.get_map_chart_data,
            "meter_chart": self.get_meter_chart_data,
            "list": self.get_list_view_data,
            "tile": self.get_tile_data,
            "kpi": self.get_kpi_data,
            "to_do": self.get_todo_data,
        }
        if conf.use_multidim and chart_type in _multidim_compatible:
            prepared_data = self.get_multidim_chart_data(conf)
        else:
            prepared_data = chart_handlers.get(chart_type, lambda x: [])(conf)
        return self._build_final_response(
            prepared_data, domain, chart_type, view_item, extra_action
        )

    def _init_configuration(self):
        """
        Configure global cong variable
        """
        conf = SimpleNamespace(
            model=self.model_id.model,
            name=self.name,
            hide_false_value=self.hide_false_value,
            show_unit=self.show_unit,
            unit_type=self.unit_type,
            custom_unit=self.custom_unit,
            layout_type=self.layout_type,
            tile_layout_type=self.tile_layout_type,
            meter_target=self.meter_target,
            text_align=self.text_align,
            background_color=self.background_color,
            is_kpi_border=self.is_kpi_border,
            kpi_border_type=self.kpi_border_type,
            kpi_border_color=self.kpi_border_color,
            kpi_border_width=self.kpi_border_width,
            font_color=self.font_color,
            font_size=self.font_size,
            font_weight=self.font_weight,
            group_by=(
                f'partner_id.{self.group_by_id.name}'
                if self.group_by_id
                    and self.group_by_id.model_id.model == 'res.partner'
                    and self.model_id.model != 'res.partner'
                else self.group_by_id.name
            ),
            group_by_is_dotted=bool(
                self.group_by_id
                and self.group_by_id.model_id.model == 'res.partner'
                and self.model_id.model != 'res.partner'
            ),
            # ── Tile group_by ──
            tile_group_by=self.tile_group_by_id.name if self.tile_group_by_id else None,
            tile_group_by_ttype=self.tile_group_by_id.ttype if self.tile_group_by_id else None,
            tile_group_mode=self.tile_group_mode or "single",
            tile_group_limit=self.tile_group_limit or 5,
            # ── Multi-dim V0 ──
            use_multidim=bool(self.dim1_link_field_id and self.dim1_group_field_id),
            dim1_link_field=self.dim1_link_field_id.name if self.dim1_link_field_id else None,
            dim1_link_col=self.dim1_link_field_id.name if self.dim1_link_field_id else None,
            dim1_related_model=self.dim1_link_field_id.relation if self.dim1_link_field_id else None,
            dim1_related_table=(
                self.env[self.dim1_link_field_id.relation]._table
                if self.dim1_link_field_id and self.dim1_link_field_id.relation
                else None
            ),
            dim1_group_field=self.dim1_group_field_id.name if self.dim1_group_field_id else None,
            dim1_group_field_ttype=self.dim1_group_field_id.ttype if self.dim1_group_field_id else None,
            dim1_group_field_relation=self.dim1_group_field_id.relation if self.dim1_group_field_id else None,
            enable_dim2=self.enable_dim2,
            dim2_link_field=self.dim2_link_field_id.name if self.dim2_link_field_id else None,
            dim2_related_model=self.dim2_link_field_id.relation if self.dim2_link_field_id else None,
            dim2_related_table=(
                self.env[self.dim2_link_field_id.relation]._table
                if self.dim2_link_field_id and self.dim2_link_field_id.relation
                else None
            ),
            dim2_group_field=self.dim2_group_field_id.name if self.dim2_group_field_id else None,
            dim2_group_field_ttype=self.dim2_group_field_id.ttype if self.dim2_group_field_id else None,
            dim2_group_field_relation=self.dim2_group_field_id.relation if self.dim2_group_field_id else None,
            dim2_time_granularity=self.dim2_time_granularity,
            use_global_date=False,
            time_range=self.time_range,
            map_group_by=self.map_group_by_id.name,
            sub_group_by=(
                f'partner_id.{self.sub_group_by_id.name}'
                if self.sub_group_by_id
                    and self.sub_group_by_id.model_id.model == 'res.partner'
                    and self.model_id.model != 'res.partner'
                else self.sub_group_by_id.name
            ),
            sub_group_by_is_dotted=bool(
                self.sub_group_by_id
                and self.sub_group_by_id.model_id.model == 'res.partner'
                and self.model_id.model != 'res.partner'
            ),
            sub_time_range=self.sub_time_range,
            measurement_field_ids=self.measurement_field_ids,
            sort_field=self.sort_field_id.name,
            sort_order=self.sort_order,
            limit_record=self.limit_record,
            date_filter_field=self.date_filter_field_id.name,
            date_filter_option=self.date_filter_option,
            domain=self.evaluate_odoo_domain(self.domain) if self.domain else [],
            data_type=self.data_type,
            company=self.company_id.id,
            measurement_field_id=self.measurement_field_id,
            include_periods=self.include_periods,
            same_period_previous_years=self.same_period_previous_years,
            list_type=self.list_type,
            icon_option=self.icon_option,
            default_icon=self.default_icon,
            icon=self.icon,
            kpi_model=self.kpi_model_id.model,
            kpi_data_type=self.kpi_data_type,
            kpi_measurement_field_id=self.kpi_measurement_field_id,
            kpi_limit_record=self.kpi_limit_record,
            kpi_domain=self.evaluate_odoo_domain(self.kpi_domain)
            if self.kpi_domain
            else [],
            kpi_date_filter_field_id=self.kpi_date_filter_field_id.name,
            kpi_date_filter_option=self.kpi_date_filter_option,
            kpi_include_periods=self.kpi_include_periods,
            kpi_same_period_previous_years=self.kpi_same_period_previous_years,
            kpi_comparison_type=self.kpi_comparison_type,
            kpi_enable_target=self.kpi_enable_target,
            kpi_target_value=self.kpi_target_value,
            kpi_view_type=self.kpi_view_type,
            previous_period_comparision=self.previous_period_comparision,
            previous_period_duration=self.previous_period_duration,
            previous_period_type=self.previous_period_type,
            is_apply_multiplier=self.is_apply_multiplier,
            todo_layout=self.todo_layout,
            todo_action_ids=[
                {
                    "name": action.name,
                    "action_line_ids": [
                        {
                            "name": action_line.name,
                            "active_record": action_line.active_record,
                        }
                        for action_line in action.action_line_ids
                    ],
                }
                for action in self.todo_action_ids
            ],
            chart_multiplier_ids=[
                {"field_id": m.field_id.id, "multiplier": m.multiplier}
                for m in self.chart_multiplier_ids
            ],
            list_measure_ids=[
                {"list_measure_id": m.list_measure_id.id, "value_type": m.value_type}
                for m in self.list_measure_ids
            ],
            list_field_ids=[
                {"list_field_id": f.list_field_id.id, "sequence": f.sequence}
                for f in self.list_field_ids
            ],
        )
        return conf, conf.domain.copy()

    def html_to_image(self):
        chart_data = self.get_chart_data(self.chart_type, self.name)
        recordsets = {
            "chart_id": self.id,
            "chart_type": self.chart_type,
            "name": self.name,
        }
        if "default_icon" in chart_data and chart_data.get("default_icon"):
            chart_data.update({"kpi_icon": Markup(chart_data.get("default_icon"))})
        recordsets.update(chart_data)
        height = "300px"
        style = "margin: 0; padding: 20px;"
        template_html = ""
        if self.chart_type == "list":
            style = "margin: 0; padding: 0;"
            records = recordsets.get("records")
            if records is None:
                image_height = 500
            else:
                image_height = 200
                if len(records) > 5:
                    image_height = 280 * (len(records) / 6)
                    if image_height < 280:
                        image_height = 280
                elif len(records) <= 2:
                    image_height = 150
            if image_height > 6000:
                recordsets.update(
                    {
                        "isError": True,
                        "errorMessage": "Such large image can not be added!",
                    }
                )
                image_height = 300
            height = "%spx" % int(image_height)

            template_html = self.env["ir.ui.view"]._render_template(
                "synconics_bi_dashboard.list_layout", {"recordsets": recordsets}
            )
            template_html = f"""<div class="col-sm-12 col-md-12 oe_inner">
                                                            {template_html}
                                                        </div>"""
        elif self.chart_type == "to_do":
            template_html = ""
            if recordsets.get("layout_type") == "activity":
                style = "margin: 0; padding: 0;"
                records = recordsets.get("records")
                image_height = 200
                if len(records) > 5:
                    image_height = 280 * (len(records) / 10)
                elif len(records) <= 2:
                    image_height = 150
                if image_height > 6000:
                    recordsets.update(
                        {
                            "isError": True,
                            "errorMessage": "Such large image can not be added!",
                        }
                    )
                    image_height = 300
                height = "%spx" % image_height

                template_html = self.env["ir.ui.view"]._render_template(
                    "synconics_bi_dashboard.to_do_layout", {"recordsets": recordsets}
                )
                template_html = f"""<div class="col-sm-12 col-md-12 oe_inner">
                                                                {template_html}
                                                            </div>"""
        else:
            kpi_layout_options = {
                "layout1": "synconics_bi_dashboard.kpi_layout_one",
                "layout2": "synconics_bi_dashboard.kpi_layout_two",
                "layout3": "synconics_bi_dashboard.kpi_layout_three",
                "layout4": "synconics_bi_dashboard.kpi_layout_four",
                "layout5": "synconics_bi_dashboard.kpi_layout_five",
            }
            tile_layout_options = {
                "layout1": "synconics_bi_dashboard.tile_layout_one",
                "layout2": "synconics_bi_dashboard.tile_layout_two",
                "layout3": "synconics_bi_dashboard.tile_layout_three",
                "layout4": "synconics_bi_dashboard.tile_layout_four",
            }
            if self.chart_type == "kpi":
                if "type" in recordsets and recordsets.get("type") == "error":
                    template_html = ""
                else:
                    template_html = self.env["ir.ui.view"]._render_template(
                        kpi_layout_options.get(self.layout_type),
                        {"recordsets": recordsets},
                    )
            else:
                if "type" in recordsets and recordsets.get("type") == "error":
                    template_html = ""
                else:
                    template_html = self.env["ir.ui.view"]._render_template(
                        tile_layout_options.get(self.tile_layout_type),
                        {"recordsets": recordsets},
                    )
            template_html = f"""<div class="col-sm-12 col-md-12 oe_inner" style="height: 89%">
                                                            {template_html}
                                                        </div>"""
        alignment_fix_css = """
            <style>
                /* Fix for imgkit flexbox alignment issues */
                .row.d-flex[style*="align-items: center"] {
                    display: table !important;
                    width: 100% !important;
                    height: 100% !important;
                }
                .row.d-flex[style*="align-items: center"] > .col-md-12,
                .row[style*="align-items"] > .col-md-12 {
                    display: table-cell !important;
                    vertical-align: middle !important;
                }

                /* Preserve text alignment */
                [style*="text-align:center"] {
                    text-align: center !important;
                }

                /* Force table layout for bottom sections */
                .o_bottom {
                    display: table !important;
                    width: 100% !important;
                    table-layout: fixed !important;
                    position: absolute;
                    bottom: 4px;
                    left: 0;
                    right: 0;
                }

                .oe_target, .oe_prev {
                    display: table-cell !important;
                    vertical-align: bottom !important;
                    width: 50% !important;
                }
                .oe_target { text-align: left !important; }
                .oe_prev { text-align: right !important; }

                /* Ensure proper spacing and alignment */
                .metric-container {
                    display: inline-block !important;
                    margin-bottom: 2px !important;
                }
            </style>
        """
        if self.layout_type == "layout1":
            alignment_fix_css = alignment_fix_css.replace(
                "</style>",
                """
                .fa-bullseye, .fa-calendar {
                    background-color: #cecece61;
                    height: auto;
                    padding: 5px;
                    size: a3;
                    font-size: 18px;
                }
                </style>
                """,
            )

        full_html = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
                {alignment_fix_css}
                <style>
                    body {{ {style} }}
                </style>
            </head>
            <body style="height: {height}; width: 100%;">
                {template_html}
            </body>
        </html>
        """

        options = {
            "encoding": "UTF-8",
            "zoom": "1",
        }
        img_binary = imgkit.from_string(full_html, False, options=options)
        img_base64 = base64.b64encode(img_binary).decode("UTF-8")
        img_data_url = f"data:image/jpeg;base64,{img_base64}"
        return img_data_url

    def _handle_dirty_data(self, conf, data):
        """
        Apply logic base on Dirty data variable
        """
        ir_model = self.env["ir.model"].sudo()
        ir_model_fields = self.env["ir.model.fields"].sudo()

        # Pré-calcul champs multi-dim (browse vide → attributs = False si non renseigné)
        _d1lf_id = data.get("dim1_link_field_id")
        _d1gf_id = data.get("dim1_group_field_id")
        _d2lf_id = data.get("dim2_link_field_id")
        _d2gf_id = data.get("dim2_group_field_id")
        # isinstance(False, int) == True en Python (bool hérite de int) → guard with `and id`
        _dim1_lf = ir_model_fields.browse(_d1lf_id) if isinstance(_d1lf_id, int) and _d1lf_id else ir_model_fields.browse()
        _dim1_gf = ir_model_fields.browse(_d1gf_id) if isinstance(_d1gf_id, int) and _d1gf_id else ir_model_fields.browse()
        _dim2_lf = ir_model_fields.browse(_d2lf_id) if isinstance(_d2lf_id, int) and _d2lf_id else ir_model_fields.browse()
        _dim2_gf = ir_model_fields.browse(_d2gf_id) if isinstance(_d2gf_id, int) and _d2gf_id else ir_model_fields.browse()

        # Pré-calcul group_by : si le champ appartient à res.partner ET que le modèle de base
        # n'est pas res.partner lui-même → chemin dotté 'partner_id.X'
        _base_model_name = (
            ir_model.browse(data.get("model_id")).model
            if data.get("model_id") else None
        )
        _gb_raw_id = data.get("group_by_id")
        _gb_field = (
            ir_model_fields.browse(_gb_raw_id)
            if isinstance(_gb_raw_id, int) and _gb_raw_id
            else ir_model_fields.browse()
        )
        _gb_is_partner = bool(
            _gb_field.id
            and _gb_field.model_id
            and _gb_field.model_id.model == 'res.partner'
            and _base_model_name != 'res.partner'
        )

        # Pré-calcul sub_group_by : même logique que group_by
        _sgb_raw_id = data.get("sub_group_by_id")
        _sgb_field = (
            ir_model_fields.browse(_sgb_raw_id)
            if isinstance(_sgb_raw_id, int) and _sgb_raw_id
            else ir_model_fields.browse()
        )
        _sgb_is_partner = bool(
            _sgb_field.id
            and _sgb_field.model_id
            and _sgb_field.model_id.model == 'res.partner'
            and _base_model_name != 'res.partner'
        )

        update_conf_dict = {
            "hide_false_value": data.get("hide_false_value"),
            "show_unit": data.get("show_unit"),
            "unit_type": data.get("unit_type"),
            "tile_layout_type": data.get("tile_layout_type", "layout1"),
            "custom_unit": data.get("custom_unit"),
            "model": ir_model.browse(data.get("model_id")).model
            if "model_id" in data
            else None,
            "domain": self.evaluate_odoo_domain(data.get("domain"))
            if "domain" in data
            else [],
            "group_by": (
                f'partner_id.{_gb_field.name}' if _gb_is_partner and _gb_field.name
                else (_gb_field.name or None)
            ) if "group_by_id" in data
            else None,
            "group_by_is_dotted": _gb_is_partner if "group_by_id" in data else False,
            "time_range": data.get("time_range"),
            "map_group_by": ir_model_fields.browse(data.get("map_group_by_id")).name
            if "map_group_by_id" in data
            else None,
            "meter_target": data.get("meter_target"),
            "font_size": data.get("font_size"),
            "font_weight": data.get("font_weight"),
            "date_filter_field": ir_model_fields.browse(
                data.get("date_filter_field_id")
            ).name
            if "date_filter_field_id" in data
            else None,
            "sub_group_by": (
                f'partner_id.{_sgb_field.name}' if _sgb_is_partner and _sgb_field.name
                else (_sgb_field.name or None)
            ) if "sub_group_by_id" in data else None,
            "sub_group_by_is_dotted": _sgb_is_partner if "sub_group_by_id" in data else False,
            "sub_time_range": data.get("sub_time_range"),
            "measurement_field_ids": ir_model_fields.browse(
                data.get("measurement_field_ids", [])
            ),
            "sort_field": ir_model_fields.browse(data.get("sort_field_id")).name
            if "sort_field_id" in data
            else None,
            "todo_layout": data.get("todo_layout", "default"),
            "todo_action_ids": data.get("todo_action_ids", []),
            "list_type": data.get("list_type", "standard"),
            "list_measure_ids": data.get("list_measure_ids", []),
            "list_field_ids": data.get("list_field_ids", []),
            "include_periods": data.get("include_periods", 0),
            "same_period_previous_years": data.get("same_period_previous_years", 0),
            "date_filter_option": data.get("date_filter_option"),
            "measurement_field_id": ir_model_fields.browse(data["measurement_field_id"])
            if isinstance(data.get("measurement_field_id"), int)
            else data.get("measurement_field_id"),
            "is_apply_multiplier": data.get("is_apply_multiplier", False),
            "chart_multiplier_ids": data.get("chart_multiplier_ids", []),
            "company": data.get("company_id"),
            "data_type": data.get("data_type", "sum"),
            "limit_record": data.get("limit_record") or 0,
            "sort_order": data.get("sort_order"),
            "name": data.get("name", ""),
            "layout_type": data.get("layout_type", "layout1"),
            "text_align": data.get("text_align", "center"),
            "background_color": data.get("background_color", "#CCC"),
            "is_kpi_border": data.get("is_kpi_border", False),
            "kpi_border_type": data.get("kpi_border_type"),
            "kpi_border_color": data.get("kpi_border_color"),
            "kpi_border_width": data.get("kpi_border_width"),
            "font_color": data.get("font_color", "#FFF"),
            "icon_option": data.get("icon_option", False),
            "default_icon": data.get("default_icon", ""),
            "icon": data.get("icon", b""),
            "kpi_model": ir_model.browse(data.get("kpi_model_id")).model
            if "kpi_model_id" in data
            else None,
            "kpi_data_type": data.get("kpi_data_type", "sum"),
            "kpi_measurement_field_id": ir_model_fields.browse(
                data["kpi_measurement_field_id"]
            )
            if isinstance(data.get("kpi_measurement_field_id"), int)
            else data.get("kpi_measurement_field_id"),
            "kpi_limit_record": data.get("kpi_limit_record") or 0,
            "kpi_domain": self.evaluate_odoo_domain(data.get("kpi_domain"))
            if "kpi_domain" in data
            else [],
            "kpi_data_filter_field_id": ir_model_fields.browse(
                data["kpi_data_filter_field_id"]
            )
            if isinstance(data.get("kpi_data_filter_field_id"), int)
            else data.get("kpi_data_filter_field_id"),
            "kpi_date_filter_option": data.get("kpi_date_filter_option"),
            "kpi_include_periods": data.get("kpi_include_periods", 0),
            "kpi_comparison_type": data.get("kpi_comparison_type", "none"),
            "kpi_enable_target": data.get("kpi_enable_target", False),
            "kpi_target_value": data.get("kpi_target_value", 0),
            "kpi_view_type": data.get("kpi_view_type", "standard"),
            "kpi_same_period_previous_years": data.get(
                "kpi_same_period_previous_years", 0
            ),
            "previous_period_comparision": data.get(
                "previous_period_comparision", False
            ),
            "previous_period_duration": data.get("previous_period_duration", 0),
            "previous_period_type": data.get("previous_period_type", "percentage"),
            # ── Tile group_by ─────────────────────────────────────────────────────
            "tile_group_by": ir_model_fields.browse(data["tile_group_by_id"]).name
            if isinstance(data.get("tile_group_by_id"), int) and data.get("tile_group_by_id")
            else None,
            "tile_group_mode": data.get("tile_group_mode", "single"),
            "tile_group_limit": data.get("tile_group_limit") or 5,
            # ── Multi-dim V0 ──────────────────────────────────────────────────────
            "use_multidim": bool(_dim1_lf.name and _dim1_gf.name),
            "dim1_link_field": _dim1_lf.name or None,
            "dim1_link_col": _dim1_lf.name or None,
            "dim1_related_model": _dim1_lf.relation or None,
            "dim1_related_table": (
                self.env[_dim1_lf.relation]._table if _dim1_lf.relation else None
            ),
            "dim1_group_field": _dim1_gf.name or None,
            "dim1_group_field_ttype": _dim1_gf.ttype or None,
            "dim1_group_field_relation": _dim1_gf.relation or None,
            "enable_dim2": data.get("enable_dim2", False),
            "dim2_link_field": _dim2_lf.name or None,
            "dim2_related_model": _dim2_lf.relation or None,
            "dim2_related_table": (
                self.env[_dim2_lf.relation]._table if _dim2_lf.relation else None
            ),
            "dim2_group_field": _dim2_gf.name or None,
            "dim2_group_field_ttype": _dim2_gf.ttype or None,
            "dim2_group_field_relation": _dim2_gf.relation or None,
            "dim2_time_granularity": data.get("dim2_time_granularity"),
        }
        for key, value in update_conf_dict.items():
            setattr(conf, key, value)

    def _process_domain(self, domain, extra_action, group_by_id):
        """
        Prepare domain
        """
        if extra_action and extra_action.get("domain"):
            domain = extra_action.get("prev_domains", domain)
            if extra_action.get("current_group_by"):
                group_by_id = group_by_id.browse(extra_action["current_group_by"])
            if group_by_id and group_by_id.ttype == "selection":
                value_name = False
                if isinstance(group_by_id.selection, str):
                    selections = safe_eval(group_by_id.selection)
                    for selection in selections:
                        if selection[1] == extra_action["domain"].get("record_id"):
                            value_name = selection[0]
                            break
                domain.append((group_by_id.name, "=", value_name))
            else:
                domain.append(
                    (group_by_id.name, "=", extra_action["domain"].get("record_id"))
                )
        return domain

    def _tile_style_dict(self, conf_obj, message=""):
        """Champs de style communs à tous les modes de tile."""
        return {
            "name": conf_obj.name,
            "background_color": conf_obj.background_color,
            "is_kpi_border": conf_obj.is_kpi_border,
            "kpi_border_type": conf_obj.kpi_border_type,
            "kpi_border_color": conf_obj.kpi_border_color,
            "kpi_border_width": conf_obj.kpi_border_width,
            "font_color": conf_obj.font_color,
            "font_size": str(conf_obj.font_size),
            "font_weight": conf_obj.font_weight,
            "text_align": conf_obj.text_align,
            "layout_type": conf_obj.layout_type,
            "tile_layout_type": conf_obj.tile_layout_type,
            "icon_option": conf_obj.icon_option,
            "default_icon": conf_obj.default_icon,
            "icon": conf_obj.icon,
            "message": message,
        }

    def _format_tile_value(self, conf_obj, value):
        """Formate une valeur numérique selon les paramètres d'unité de la tile."""
        value = round(float(value), 2)
        if not conf_obj.show_unit:
            return value
        if conf_obj.unit_type == "monetary":
            company = self.env["res.company"].browse(conf_obj.company)
            return format_amount(self.env, value, company.currency_id)
        return f"{conf_obj.custom_unit or ''} {value}"

    def _get_tile_grouped_data(self, conf_obj, domain, record_obj, today_date=False):
        """
        Agrège les enregistrements par groupe via read_group(lazy=False).

        lazy=False : toutes les dimensions groupby en une seule requête SQL.
        Pas de sous-groupes, résultat plat → facile à pivoter.

        Erreurs fréquentes :
        - orderby='__count' non supporté → tri en Python après
        - many2one retourne (id, name) tuple → unwrapper
        - selection retourne la clé brute → chercher le libellé dans field.selection
        - today_date est une date Python → ajouter comme domaine date pour le SQL

        Retourne (sorted_groups, total_count) SANS limitation — le caller limite.
        """
        if today_date and conf_obj.date_filter_field:
            domain = domain + [(conf_obj.date_filter_field, "=", today_date)]

        group_field = conf_obj.tile_group_by
        if conf_obj.data_type == "count_distinct" and conf_obj.measurement_field_id:
            # COUNT(DISTINCT) non supporté par read_group → SQL
            sql_rows = self._count_distinct_sql(
                record_obj, domain,
                group_field=group_field,
                distinct_field=conf_obj.measurement_field_id.name,
            )
            # sql_rows = [(group_raw, count_int), ...] déjà triés DESC
            field_obj = record_obj._fields.get(group_field)
            result = []
            for raw_label, cnt in sql_rows:
                if raw_label is None or raw_label is False:
                    label = "N/A"
                elif field_obj and field_obj.type == 'many2one' and field_obj.comodel_name:
                    rec = self.env[field_obj.comodel_name].browse(raw_label)
                    label = rec.display_name or str(raw_label)
                elif field_obj and hasattr(field_obj, 'selection') and field_obj.selection:
                    selections = field_obj.selection
                    if callable(selections):
                        selections = selections(record_obj)
                    label = dict(selections).get(raw_label, str(raw_label))
                else:
                    label = str(raw_label)
                raw_val = float(cnt or 0)
                result.append({
                    "label": label,
                    "count": self._format_tile_value(conf_obj, raw_val),
                    "raw": round(raw_val, 2),
                })
            return result, len(result)

        if conf_obj.data_type == "count":
            fields_list = [group_field]
            agg_key = "__count"
        elif conf_obj.data_type == "sum":
            fields_list = [group_field, f"{conf_obj.measurement_field_id.name}:sum"]
            agg_key = conf_obj.measurement_field_id.name
        else:  # average
            fields_list = [group_field, f"{conf_obj.measurement_field_id.name}:avg"]
            agg_key = conf_obj.measurement_field_id.name

        # Supprimer group_by du contexte pour éviter toute interférence Odoo
        raw_groups = record_obj.with_context(group_by=None).read_group(
            domain=domain,
            fields=fields_list,
            groupby=[group_field],
            lazy=False,
        )

        # Tri décroissant par valeur agrégée (orderby='__count' non supporté directement)
        raw_groups.sort(key=lambda g: g.get(agg_key, 0) or 0, reverse=True)
        total = len(raw_groups)

        # Résolution des libellés selon le type du champ
        field_obj = record_obj._fields.get(group_field)

        result = []
        for g in raw_groups:
            raw_label = g.get(group_field)
            if raw_label is False or raw_label is None:
                label = "N/A"
            elif isinstance(raw_label, tuple):
                # many2one → (id, "display_name")
                label = raw_label[1] if raw_label[1] else str(raw_label[0])
            elif field_obj and hasattr(field_obj, "selection") and field_obj.selection:
                # selection → lookup libellé depuis la définition du champ
                selections = field_obj.selection
                if callable(selections):
                    selections = selections(record_obj)
                label = dict(selections).get(raw_label, str(raw_label))
            else:
                label = str(raw_label)

            raw_val = float(g.get(agg_key, 0) or 0)
            if conf_obj.is_apply_multiplier and conf_obj.chart_multiplier_ids:
                raw_val *= conf_obj.chart_multiplier_ids[0].get("multiplier", 1)

            result.append({
                "label": label,
                "count": self._format_tile_value(conf_obj, raw_val),
                "raw": round(raw_val, 2),
            })

        return result, total

    def get_tile_data(self, conf_obj, previous=0):
        """
        Calculate and get data for the Tile view.
        Supporte 3 modes : single (défaut), grouped (liste), top (valeur max).
        """
        if not conf_obj.model:
            return {"type": "error", "message": "Please Select model!"}
        if not conf_obj.measurement_field_id and conf_obj.data_type in [
            "sum",
            "average",
        ]:
            return {"type": "error", "message": "Please Select measurement!"}
        record_obj = self.env[conf_obj.model]
        message = ""
        today_date = False
        domain = conf_obj.domain.copy()
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))

        if (
            not getattr(conf_obj, "use_global_date", False)
            and conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_filter_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
                previous,
            )
            if date_filter_domain.get("domain"):
                start_date = date_filter_domain.get("start_date")
                end_date = date_filter_domain.get("end_date")
                message = "%s to %s" % (
                    start_date.strftime("%d %b, %y"),
                    end_date.strftime("%d %b, %y"),
                )
                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_filter_domain["domain"])
                else:
                    today_date = start_date.date()

        # ── Dispatch grouped / top ──────────────────────────────────────────────
        tile_group_mode = getattr(conf_obj, "tile_group_mode", "single")
        tile_group_by = getattr(conf_obj, "tile_group_by", None)

        if tile_group_mode != "single" and tile_group_by:
            if conf_obj.data_type != "count" and not conf_obj.measurement_field_id:
                return {"type": "error", "message": "Please Select measurement!"}
            groups, total = self._get_tile_grouped_data(
                conf_obj, domain, record_obj, today_date=today_date
            )
            limit = max(getattr(conf_obj, "tile_group_limit", 5) or 5, 1)
            style = self._tile_style_dict(conf_obj, message)

            if tile_group_mode == "grouped":
                return {
                    **style,
                    "tile_mode": "grouped",
                    "groups": groups[:limit],
                    "has_more": total > limit,
                    "hidden_count": max(total - limit, 0),
                }
            else:  # top
                top = groups[0] if groups else {"label": "—", "count": "—", "raw": 0}
                return {
                    **style,
                    "tile_mode": "top",
                    "count": top["count"],
                    "calculated_count": top["raw"],
                    "top_label": top["label"],
                }

        # ── Mode single (comportement original) ─────────────────────────────────
        all_records = record_obj.search(domain)
        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]

        count = 0
        if conf_obj.data_type == "count":
            count = len(all_records)
        elif conf_obj.data_type in ["sum", "average"]:
            count_list = []
            for record in all_records:
                val = getattr(record, conf_obj.measurement_field_id.name)
                if isinstance(val, models.Model):
                    val = 0
                elif val is False or val is None:
                    val = 0
                count_list.append(val)
            count = sum(count_list)
            if conf_obj.data_type == "average" and count != 0:
                count /= len(count_list)
        elif conf_obj.data_type == "count_distinct" and conf_obj.measurement_field_id:
            mf_name = conf_obj.measurement_field_id.name
            mf_field = record_obj._fields.get(mf_name)
            if mf_field and mf_field.type == 'many2one':
                count = len(set(all_records.mapped(mf_name).ids))
            else:
                count = len({v for v in all_records.mapped(mf_name) if v is not False and v is not None})
        if conf_obj.is_apply_multiplier and conf_obj.chart_multiplier_ids:
            if conf_obj.data_type in ["count", "sum", "average", "count_distinct"]:
                count *= conf_obj.chart_multiplier_ids[0].get("multiplier")
        count_with_symbol = round(count, 2)
        if conf_obj.show_unit:
            if conf_obj.unit_type == "monetary":
                company = self.env["res.company"].browse(conf_obj.company)
                count_with_symbol = format_amount(
                    record_obj.env, count_with_symbol, company.currency_id
                )
            else:
                count_with_symbol = "%s %s" % (
                    conf_obj.custom_unit or "",
                    count_with_symbol,
                )
        return {
            **self._tile_style_dict(conf_obj, message),
            "tile_mode": "single",
            "count": count_with_symbol,
            "calculated_count": round(count, 2),
        }

    def get_kpi_data(self, conf_obj):
        """
        Calculate and get data for KPI view
        """

        def calc_ratio(tile_count, kpi_count2):
            """
            Calculation to calculate Ratio
            """
            n = gcd(int(tile_count), int(kpi_count2))
            return int(tile_count // n), int(kpi_count2 // n)

        def get_count2(records, conf):
            """
            Calculate second KPI data
            """
            if conf.kpi_data_type == "count":
                return len(records)
            elif conf.kpi_data_type in ("sum", "average"):
                values = []
                for rec in records:
                    val = getattr(rec, conf.kpi_measurement_field_id.name)
                    if isinstance(val, models.Model):
                        val = 0
                    elif val is False or val is None:
                        val = 0
                    values.append(val)
                total = sum(values)
                return (
                    total / len(values)
                    if conf.kpi_data_type == "average" and values
                    else total
                )
            elif conf.kpi_data_type == "count_distinct" and conf.kpi_measurement_field_id:
                mf_name = conf.kpi_measurement_field_id.name
                mf_field = records._fields.get(mf_name) if records else None
                if mf_field and mf_field.type == 'many2one':
                    return len(set(records.mapped(mf_name).ids))
                return len({v for v in records.mapped(mf_name) if v is not False and v is not None})
            return 0

        prepared_data = self.get_tile_data(conf_obj)
        if prepared_data and prepared_data.get("type") == "error":
            return prepared_data

        if conf_obj.previous_period_comparision:
            updated_data = self.get_tile_data(
                conf_obj, conf_obj.previous_period_duration
            )
            if isinstance(updated_data, dict) and "type" in updated_data:
                updated_data.update(
                    {"calculated_count": 0, "message": updated_data["date_message"]}
                )
            if isinstance(updated_data, dict):
                standard = round(updated_data.get("calculated_count"), 2)
                if conf_obj.previous_period_type == "percentage":
                    standard = (
                        str(
                            round(
                                (updated_data.get("calculated_count") * 100)
                                / prepared_data.get("calculated_count"),
                                2,
                            )
                        )
                        + "%"
                        if prepared_data.get("calculated_count")
                        else "0 %"
                    )
                elif conf_obj.show_unit:
                    if conf_obj.unit_type == "monetary":
                        record_obj = self.env[conf_obj.model]
                        company = self.env["res.company"].browse(conf_obj.company)
                        standard = format_amount(
                            record_obj.env, standard, company.currency_id
                        )
                    else:
                        standard = "%s %s" % (
                            conf_obj.custom_unit or "",
                            standard,
                        )
                arrow = (
                    "up"
                    if prepared_data.get("calculated_count")
                    > updated_data.get("calculated_count")
                    else "down"
                )
                previous_data = {
                    "arrow": arrow,
                    "standard": standard,
                }
                if "message" in updated_data and updated_data.get("message"):
                    previous_data["message"] = updated_data["message"]
                prepared_data.update({"previous_data": previous_data})

        if not conf_obj.kpi_model:
            if conf_obj.kpi_enable_target:
                if conf_obj.kpi_view_type == "progress":
                    compute_count = prepared_data["calculated_count"]
                    target_value = conf_obj.kpi_target_value
                    progress = (
                        int(round((compute_count / target_value) * 100))
                        if target_value != 0
                        else 0
                    )
                    # if kcmp_type != "sum":
                    #     progress = int(compute_count) if compute_count else 0
                    prepared_data.update(
                        {
                            "kpi_view_type": "progress",
                            "progress": progress,
                            "kpi_enable_target": False,
                        }
                    )
                    # prepared_data.pop('previous_data')
                else:
                    compute_count = prepared_data["calculated_count"]
                    target_value = conf_obj.kpi_target_value
                    color, arrow = (
                        ("red", "down")
                        if (target_value - compute_count) > 0
                        else ("green", "up")
                    )
                    standard = (
                        str(
                            round(
                                (compute_count * 100) / target_value
                                if target_value != 0
                                else 1,
                                2,
                            )
                        )
                        + "%"
                    )
                    prepared_data.update(
                        {
                            "kpi_view_type": "standard",
                            "standard": standard,
                            "kpi_enable_target": False,
                            "color": color,
                            "arrow": arrow,
                        }
                    )
            return prepared_data

        if not conf_obj.kpi_measurement_field_id and conf_obj.kpi_data_type in (
            "sum",
            "average",
        ):
            return {"type": "error", "message": "Please Select measurement!"}

        record_obj = self.env[conf_obj.kpi_model]
        domain = conf_obj.kpi_domain[:]
        kpi_today_date = False
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.kpi_date_filter_field_id
            and conf_obj.kpi_date_filter_option
            and conf_obj.kpi_date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.kpi_date_filter_field_id,
                conf_obj.kpi_date_filter_option,
                conf_obj.kpi_include_periods,
                conf_obj.kpi_same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain += date_domain["domain"]
                else:
                    kpi_today_date = start_date.date()

        all_records = record_obj.search(domain)
        if kpi_today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.kpi_date_filter_field_id)
                and (
                    getattr(record, conf_obj.kpi_date_filter_field_id).date()
                    if isinstance(
                        getattr(record, conf_obj.kpi_date_filter_field_id), datetime
                    )
                    else getattr(record, conf_obj.kpi_date_filter_field_id)
                )
                == kpi_today_date
            )

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=conf_obj.sort_order == "desc",
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.kpi_limit_record > 0:
            all_records = all_records[: conf_obj.kpi_limit_record]

        count = prepared_data.get("calculated_count", 0)
        count2 = get_count2(all_records, conf_obj)
        compute_count = 0
        symbol = ""
        if conf_obj.show_unit:
            if conf_obj.unit_type == "monetary":
                company = self.env["res.company"].browse(conf_obj.company)
                symbol = "%s" % company.currency_id.symbol
            else:
                symbol = "%s" % (conf_obj.custom_unit or "")
        kcmp_type = conf_obj.kpi_comparison_type
        if kcmp_type == "sum":
            compute_count = count + count2
            prepared_data["count"] = "%s %s" % (symbol, round(compute_count, 2))
        elif kcmp_type == "percentage" and count2:
            compute_count = int((count / count2) * 100) if count2 else 0
            prepared_data["count"] = round(compute_count, 2)
        elif kcmp_type == "ratio" and count:
            compute_count, count2 = calc_ratio(count, count2)
            prepared_data.update(
                {
                    "count": "%s %s" % (symbol, round(compute_count, 2)),
                    "count2": "%s %s" % (symbol, count2),
                }
            )
        else:
            prepared_data["count2"] = round(count2, 2)

        if conf_obj.kpi_enable_target and kcmp_type in ("sum", "percentage"):
            target_value = conf_obj.kpi_target_value
            if conf_obj.kpi_enable_target == "percentage" and target_value > 100:
                target_value = 100

            color, arrow = (
                ("red", "down")
                if (target_value - compute_count) > 0
                else ("green", "up")
            )
            prepared_data.update(
                {"color": color, "arrow": arrow, "message": "vs Target"}
            )
            if conf_obj.kpi_view_type == "standard":
                diff = target_value - compute_count
                if diff <= 0:
                    diff = abs(diff)
                percent = round((diff / (target_value or 1)) * 100, 2)
                prepared_data["standard"] = f"{percent}%"
                if kcmp_type != "sum":
                    prepared_data["standard"] = min(target_value, 100)
            else:
                progress = (
                    int(round((compute_count / target_value) * 100))
                    if target_value != 0
                    else 0
                )
                if kcmp_type != "sum":
                    progress = int(compute_count) if compute_count else 0
                prepared_data.update({"progress": progress, "target": target_value})

        if conf_obj.is_apply_multiplier and conf_obj.chart_multiplier_ids:
            if conf_obj.data_type in ["count", "sum", "average", "count_distinct"]:
                # prepared_data["count"] = float(prepared_data.get("count", 0)) * conf_obj.chart_multiplier_ids[0].get(
                #     "multiplier"
                # )
                count_multiply = (
                    round(compute_count, 2)
                    if compute_count
                    else float(prepared_data.get("calculated_count", 0))
                )
                prepared_data["count"] = count_multiply * conf_obj.chart_multiplier_ids[
                    0
                ].get("multiplier")

        prepared_data.update(
            {
                "comparison": kcmp_type,
                "kpi_view_type": conf_obj.kpi_view_type,
                "kpi_enable_target": conf_obj.kpi_enable_target,
            }
        )
        return prepared_data

    def get_todo_data(self, conf_obj):
        """
        Calculate and get TODO data
        """
        if conf_obj.todo_layout == "default" and not conf_obj.todo_action_ids:
            return {"type": "error", "message": "No Data found!"}
        if conf_obj.todo_layout == "activity" and not conf_obj.model:
            return {"type": "error", "message": "Please select Model!"}

        if conf_obj.todo_layout == "default":
            return {
                "layout_type": conf_obj.todo_layout,
                "name": conf_obj.name,
                "records": conf_obj.todo_action_ids,
            }

        today_date = False
        domain = conf_obj.domain
        record_obj = self.env[conf_obj.model]
        activities_domain = [("res_model", "=", conf_obj.model)]
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            # domain.extend(date_domain["domain"])
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")
                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    activities_domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        records = record_obj.search(
            domain,
        )
        if today_date:
            records = records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        activities_domain.extend([("res_id", "in", records.ids)])
        if conf_obj.limit_record == 0:
            activities = self.env["mail.activity"].search(
                activities_domain,
                order="create_date %s" % (conf_obj.sort_order or ""),
            )
        else:
            activities = self.env["mail.activity"].search(
                activities_domain,
                limit=conf_obj.limit_record or 100,
                order="create_date %s" % (conf_obj.sort_order or ""),
            )
        activities_data = [
            {
                "date": record.date_deadline,
                "summary": record.summary or "",
                "name": record.res_name,
                "username": record.user_id.name,
                "activity_type": record.activity_type_id.name,
            }
            for record in activities
        ]
        if not activities_data:
            return {"type": "error", "message": "No Data to display!"}
        return {
            "layout_type": conf_obj.todo_layout,
            "name": conf_obj.name,
            "records": activities_data,
        }

    def _get_view_item(self, extra_action):
        """
        To get chart views
        """
        if extra_action and self.item_view_action_ids:
            view_index = len(extra_action.get("breadcrump_ids", []))
            return (
                self.item_view_action_ids[view_index]
                if view_index < len(self.item_view_action_ids)
                else None
            )
        return None

    def _build_final_response(
        self, prepared_data, domain, chart_type, view_item, extra_action
    ):
        """
        Calculate final response for charts data
        """
        if not extra_action:
            return prepared_data
        if view_item:
            return {
                "prepared_data": prepared_data,
                "current_domain": domain,
                "current_group_by": view_item.group_by_id.id,
                "chart_type": view_item.chart_type,
                "breadcrump_ids": view_item.id,
            }
        if self.item_action_id:
            action = self.item_action_id.read()[0]
            action["domain"] = (
                self.evaluate_odoo_domain(action["domain"] or "[]")
            ) + domain
            return {"type": "action", "action": action}
        return prepared_data

    def get_measurement_fields(
        self,
        conf_obj,
        record,
        grouped_data,
        record_group_by,
        sub_groupby,
        measurement_multiplier_value,
    ):
        """
        Calculate Measurement fields
        """
        for measurement in conf_obj.measurement_field_ids:
            field_desc = measurement.field_description
            measure_value = getattr(record, measurement.name)
            multiplier = 1
            if conf_obj.is_apply_multiplier:
                matched = next(
                    (
                        m
                        for m in conf_obj.chart_multiplier_ids
                        if m.get("field_id") == measurement.id
                    ),
                    None,
                )
                if matched:
                    multiplier = matched.get("multiplier", 1)
                    if conf_obj.data_type == "sum":
                        measure_value *= multiplier
                    elif conf_obj.data_type == "average":
                        measurement_multiplier_value[field_desc] = multiplier
            key = (
                f"{sub_groupby} - {field_desc}"
                if conf_obj.sub_group_by
                else f" - {field_desc}"
            )
            if conf_obj.data_type == "sum":
                grouped_data[record_group_by][key] += measure_value
            elif conf_obj.data_type == "average":
                grouped_data[record_group_by].setdefault(key, []).append(measure_value)
        return grouped_data, measurement_multiplier_value

    def check_conf_obj(self, conf_obj, check_measure=False):
        """
        Check conf object data.
        check_measure=True  → utilise measurement_field_id  (singular, pour funnel/pie/…)
        check_measure=False → utilise measurement_field_ids (plural M2M, pour bar/column/…)
                              avec fallback sur measurement_field_id si le plural est vide.
        """
        check_constraint = False
        if not conf_obj.model:
            return {"type": "error", "message": "Please Select Model!"}

        if conf_obj.data_type != "count":
            if check_measure:
                has_measure = bool(conf_obj.measurement_field_id)
            else:
                # Fallback: accepte le singular quand le plural est vide
                has_measure = bool(conf_obj.measurement_field_ids) or bool(conf_obj.measurement_field_id)
            if not has_measure:
                check_constraint = {
                    "type": "error",
                    "message": "Please Select Measurements!",
                }

        if (
            not conf_obj.group_by
            and conf_obj.chart_type not in ["map_chart", "meter_chart"]
        ) or (conf_obj.chart_type == "map_chart" and not conf_obj.map_group_by):
            check_constraint = {"type": "error", "message": "Please Select Group by!"}
        return check_constraint

    def _get_dim_info(self, model_name, field_path, dim_alias, time_range=None):
        """
        Analyzes a field path ('field' or 'link_field.target_field') and returns
        SQL components (JOINs, SELECT expressions, label resolution info) for groupby.
        Returns None when the path is invalid or the field does not exist.
        """
        if not field_path:
            return None
        parts = field_path.split('.') if '.' in field_path else [field_path]
        base_model = self.env[model_name]

        def _date_exprs(sql_expr, tr):
            trunc_map = {'day': 'day', 'week': 'week', 'month': 'month', 'quarter': 'quarter', 'year': 'year'}
            fmt_map = {'day': 'YYYY-MM-DD', 'week': 'IYYY-"W"IW', 'month': 'YYYY-MM', 'quarter': 'YYYY-"Q"Q', 'year': 'YYYY'}
            if tr in trunc_map:
                grp = f"DATE_TRUNC('{trunc_map[tr]}', {sql_expr})"
                lbl = f"TO_CHAR({grp}, '{fmt_map[tr]}')"
                return grp, lbl
            return sql_expr, f'CAST({sql_expr} AS TEXT)'

        info = {
            'joins': [], 'field_type': None, 'selection_map': {},
            'needs_label_col': False,
            'val_alias': f'{dim_alias}_val', 'label_alias': f'{dim_alias}_label',
            'group_expr': None, 'label_expr': None,
        }

        if len(parts) == 1:
            fld = base_model._fields.get(parts[0])
            if not fld:
                return None
            info['field_type'] = fld.type
            val_expr = f'base."{parts[0]}"'
            info['group_expr'] = val_expr
            info['label_expr'] = val_expr

            if fld.type == 'many2many':
                cm = self.env[fld.comodel_name]
                info['joins'] = [
                    f'LEFT JOIN "{fld.relation}" m2m_{dim_alias} ON base.id = m2m_{dim_alias}."{fld.column1}"',
                    f'LEFT JOIN "{cm._table}" cm_{dim_alias} ON m2m_{dim_alias}."{fld.column2}" = cm_{dim_alias}.id',
                ]
                info['group_expr'] = f'cm_{dim_alias}.id'
                info['label_expr'] = f'cm_{dim_alias}.name'
                info['needs_label_col'] = True
            elif fld.type == 'many2one':
                cm = self.env[fld.comodel_name]
                info['joins'] = [f'LEFT JOIN "{cm._table}" cm_{dim_alias} ON base."{parts[0]}" = cm_{dim_alias}.id']
                info['group_expr'] = f'base."{parts[0]}"'
                info['label_expr'] = f'cm_{dim_alias}.name'
                info['needs_label_col'] = True
            elif fld.type == 'selection':
                sel = fld.selection
                if callable(sel):
                    sel = sel(base_model)
                info['selection_map'] = dict(sel or [])
            elif fld.type in ('date', 'datetime'):
                grp, lbl = _date_exprs(val_expr, time_range)
                info['group_expr'] = grp
                info['label_expr'] = lbl
                if grp != lbl:
                    info['needs_label_col'] = True
            return info

        if len(parts) == 2:
            link_name, target_name = parts
            link_fld = base_model._fields.get(link_name)
            if not link_fld or link_fld.type != 'many2one':
                return None
            link_model = self.env[link_fld.comodel_name]
            lk = f'lk_{dim_alias}'
            info['joins'].append(f'LEFT JOIN "{link_model._table}" {lk} ON base."{link_name}" = {lk}.id')

            target_fld = link_model._fields.get(target_name)
            if not target_fld:
                return None
            info['field_type'] = target_fld.type
            info['group_expr'] = f'{lk}."{target_name}"'
            info['label_expr'] = f'{lk}."{target_name}"'

            if target_fld.type == 'many2many':
                cm = self.env[target_fld.comodel_name]
                info['joins'] += [
                    f'LEFT JOIN "{target_fld.relation}" m2m_{dim_alias} ON {lk}.id = m2m_{dim_alias}."{target_fld.column1}"',
                    f'LEFT JOIN "{cm._table}" cm_{dim_alias} ON m2m_{dim_alias}."{target_fld.column2}" = cm_{dim_alias}.id',
                ]
                info['group_expr'] = f'cm_{dim_alias}.id'
                info['label_expr'] = f'cm_{dim_alias}.name'
                info['needs_label_col'] = True
            elif target_fld.type == 'many2one':
                cm = self.env[target_fld.comodel_name]
                info['joins'].append(f'LEFT JOIN "{cm._table}" cm_{dim_alias} ON {lk}."{target_name}" = cm_{dim_alias}.id')
                info['group_expr'] = f'{lk}."{target_name}"'
                info['label_expr'] = f'cm_{dim_alias}.name'
                info['needs_label_col'] = True
            elif target_fld.type == 'selection':
                sel = target_fld.selection
                if callable(sel):
                    sel = sel(link_model)
                info['selection_map'] = dict(sel or [])
            elif target_fld.type in ('date', 'datetime'):
                expr = f'{lk}."{target_name}"'
                grp, lbl = _date_exprs(expr, time_range)
                info['group_expr'] = grp
                info['label_expr'] = lbl
                if grp != lbl:
                    info['needs_label_col'] = True
            return info

        return None

    def _resolve_dim_label(self, row, dim_info):
        """Resolves display label for a dimension from a SQL result row."""
        raw_val = row.get(dim_info['val_alias'])
        if raw_val is None:
            return False
        if dim_info['field_type'] == 'selection':
            label = dim_info['selection_map'].get(str(raw_val))
            return label if label is not None else raw_val
        if dim_info['needs_label_col']:
            label = row.get(dim_info['label_alias'])
            return label if label is not None else raw_val
        return raw_val

    def _get_grouped_list_data_sql(self, conf_obj, record_ids):
        """
        SQL-based 2-level grouped list, designed for millions of rows.
        Uses raw SQL with dynamic JOINs — ORM only for domain/ACL filtering (record_ids).
        Returns a flat list with '_level' (0=group, 1=subgroup) and '_label' keys.
        """
        if not record_ids:
            return []

        model = conf_obj.model
        base_table = self.env[model]._table

        dim1_info = self._get_dim_info(
            model, conf_obj.group_by, 'dim1',
            getattr(conf_obj, 'time_range', None)
        )
        if not dim1_info:
            return []

        sub_gb = getattr(conf_obj, 'sub_group_by', None)
        dim2_info = None
        if sub_gb:
            dim2_info = self._get_dim_info(
                model, sub_gb, 'dim2',
                getattr(conf_obj, 'sub_time_range', None)
            )

        ir_fields_obj = self.env['ir.model.fields'].sudo()
        measures = []
        for m in conf_obj.list_measure_ids:
            mfield = ir_fields_obj.browse(m.get('list_measure_id'))
            if mfield.exists():
                measures.append({
                    'field_name': mfield.name,
                    'value_type': m.get('value_type', 'sum'),
                    'label': mfield.field_description,
                })

        # Deduplicate JOINs (dim1 + dim2 may share the partner table)
        all_joins = []
        seen_joins = set()
        for j in dim1_info['joins'] + (dim2_info['joins'] if dim2_info else []):
            if j not in seen_joins:
                all_joins.append(j)
                seen_joins.add(j)

        # Build SELECT
        sel = []
        sel.append(f'{dim1_info["group_expr"]} AS {dim1_info["val_alias"]}')
        if dim1_info['needs_label_col']:
            sel.append(f'{dim1_info["label_expr"]} AS {dim1_info["label_alias"]}')
        if dim2_info:
            sel.append(f'{dim2_info["group_expr"]} AS {dim2_info["val_alias"]}')
            if dim2_info['needs_label_col']:
                sel.append(f'{dim2_info["label_expr"]} AS {dim2_info["label_alias"]}')
        for m in measures:
            fn = m['field_name']
            sel.append(f'SUM(COALESCE(base."{fn}", 0)) AS "m_{fn}"')
            if m['value_type'] == 'average':
                sel.append(f'COUNT(CASE WHEN base."{fn}" IS NOT NULL THEN 1 END) AS "cnt_{fn}"')
        sel.append('ARRAY_AGG(DISTINCT base.id) AS record_ids')

        # Build GROUP BY
        gb = [dim1_info['group_expr']]
        if dim1_info['needs_label_col']:
            gb.append(dim1_info['label_expr'])
        if dim2_info:
            gb.append(dim2_info['group_expr'])
            if dim2_info['needs_label_col']:
                gb.append(dim2_info['label_expr'])

        order_sql = f"{dim1_info['group_expr']} NULLS LAST"
        if dim2_info:
            order_sql += f', {dim2_info["group_expr"]} NULLS LAST'

        joins_sql = '\n'.join(all_joins)
        query = f"""
            SELECT {', '.join(sel)}
            FROM "{base_table}" base
            {joins_sql}
            WHERE base.id IN %s
            GROUP BY {', '.join(gb)}
            ORDER BY {order_sql}
        """
        self.env.cr.execute(query, (tuple(record_ids),))
        rows = self.env.cr.dictfetchall()

        # Pivot into flat intercalated list
        from collections import OrderedDict
        d1_groups = OrderedDict()
        for row in rows:
            key = row.get(dim1_info['val_alias'])
            if key not in d1_groups:
                d1_groups[key] = []
            d1_groups[key].append(row)

        flat = []
        for idx1, (d1_raw, group_rows) in enumerate(d1_groups.items()):
            d1_label = self._resolve_dim_label(group_rows[0], dim1_info)

            grp_rec = {
                'id': f'g0_{idx1}',
                '_level': 0,
                '_label': d1_label if d1_label is not False else '(Vide)',
                'currentIds': [],
            }
            for m in measures:
                fn = m['field_name']
                total = sum(r.get(f'm_{fn}') or 0 for r in group_rows)
                if m['value_type'] == 'average':
                    cnt = sum(r.get(f'cnt_{fn}') or 0 for r in group_rows)
                    grp_rec[fn] = round(total / cnt, 2) if cnt else 0
                else:
                    grp_rec[fn] = round(total, 2)
            for r in group_rows:
                grp_rec['currentIds'].extend(r.get('record_ids') or [])
            grp_rec['currentIds'] = list(set(grp_rec['currentIds']))
            flat.append(grp_rec)

            if dim2_info:
                for idx2, sub_row in enumerate(group_rows):
                    d2_label = self._resolve_dim_label(sub_row, dim2_info)
                    sub_rec = {
                        'id': f'g1_{idx1}_{idx2}',
                        '_level': 1,
                        '_label': d2_label if d2_label is not False else '(Vide)',
                        'currentIds': list(sub_row.get('record_ids') or []),
                    }
                    for m in measures:
                        fn = m['field_name']
                        val = sub_row.get(f'm_{fn}') or 0
                        if m['value_type'] == 'average':
                            cnt = sub_row.get(f'cnt_{fn}') or 0
                            sub_rec[fn] = round(val / cnt, 2) if cnt else 0
                        else:
                            sub_rec[fn] = round(val, 2)
                    flat.append(sub_rec)

        return flat

    def get_list_view_data(self, conf_obj):
        """
        This function is used in preparing data for List view
        """
        if not conf_obj.model:
            return {"type": "error", "message": "Please Select Model!"}
        if (conf_obj.list_type == "standard" and not conf_obj.list_field_ids) or (
            conf_obj.list_type == "grouped" and not conf_obj.list_measure_ids
        ):
            return {"type": "error", "message": "Please configure fields to display!"}
        if conf_obj.list_type == "grouped" and not conf_obj.group_by:
            return {"type": "error", "message": "Please Select Group by!"}
        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            not getattr(conf_obj, "use_global_date", False)
            and conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")
                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        records = record_obj.search(domain)
        if today_date:
            records = records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not records:
            return {"type": "error", "message": "No Data to display!"}

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = records.filtered(
                lambda rft: getattr(rft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= records.filtered(
                lambda rft: not getattr(rft, conf_obj.sort_field)
            )
            records = sorted_record
        if conf_obj.limit_record > 0:
            records = records[: conf_obj.limit_record]
        columns = []
        # column_names = []
        record_list = []
        ir_model_fields_obj = self.env["ir.model.fields"].sudo()
        if conf_obj.list_type == "standard":
            list_field_ids = sorted(
                conf_obj.list_field_ids, key=lambda x: x.get("sequence")
            )
            column_ids = [column.get("list_field_id") for column in list_field_ids]
            for column in column_ids:
                column_rec = ir_model_fields_obj.browse(column)
                columns.append(
                    {
                        "id": column_rec.id,
                        "column_name": column_rec.name,
                        "name": column_rec.field_description,
                    }
                )
            for record in records:
                record_set = {"id": record.id}
                for column in columns:
                    record_column_value = getattr(record, column.get("column_name"))
                    if isinstance(record_column_value, models.Model):
                        record_column_value = record_column_value.display_name
                    record_set.update(
                        {column.get("column_name"): record_column_value or ""}
                    )
                record_set["currentIds"] = [record.id]
                record_list.append(record_set)
        else:
            # --- Grouped mode: SQL-based 2-level aggregation (handles millions of rows) ---
            gb_path = conf_obj.group_by or ''
            gb_target_name = gb_path.split('.')[-1] if gb_path else gb_path
            # Look for field description in both the base model and res.partner (dotted path)
            gb_field_rec = ir_model_fields_obj.search([
                ('name', '=', gb_target_name),
                ('model', 'in', [conf_obj.model, 'res.partner']),
            ], limit=1)
            gb_col_label = gb_field_rec.field_description if gb_field_rec else "Groupe"

            columns.append({
                "id": 0,
                "column_name": "_label",
                "name": gb_col_label,
                "is_group_col": True,
            })
            for column in conf_obj.list_measure_ids:
                column_rec = ir_model_fields_obj.browse(column.get("list_measure_id"))
                columns.append({
                    "id": column_rec.id,
                    "column_name": column_rec.name,
                    "name": column_rec.field_description,
                    "value_type": column.get("value_type"),
                })
            record_list = self._get_grouped_list_data_sql(conf_obj, records.ids)
        return {
            "columns": columns,
            "records": record_list,
            "name": conf_obj.name,
            "model": conf_obj.model,
        }

    def get_measurement_group_data(self, conf_obj):
        """
        This function is used in preparing data for following charts
        Area Chart
        Bar Chart
        Column Chart
        Doughnut Chart
        Line Chart
        StackedColumn Chart
        Radial Chart
        Scatter Chart
        """
        check_constraint = self.check_conf_obj(conf_obj)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            not getattr(conf_obj, "use_global_date", False)
            and conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        records = record_obj.search(domain)
        if today_date:
            records = records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not records:
            return {"type": "error", "message": "No Data to display!"}

        measurement_multiplier_value = {}

        grouped_data = defaultdict(lambda: defaultdict(float))
        # Accumule les valeurs distinctes par (group_key, series_key) pour count_distinct
        distinct_sets = defaultdict(lambda: defaultdict(set))

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = records.filtered(
                lambda rft: getattr(rft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=conf_obj.sort_order == "desc",
            )
            sorted_record |= records.filtered(
                lambda rft: not getattr(rft, conf_obj.sort_field)
            )
            records = sorted_record
        if conf_obj.hide_false_value:
            _gb = conf_obj.group_by
            _is_dotted = getattr(conf_obj, "group_by_is_dotted", False)
            if _is_dotted:
                records = records.filtered(
                    lambda nonz, _gb=_gb: self._get_nested_value(nonz, _gb)
                )
            else:
                records = records.filtered(lambda nonz: getattr(nonz, _gb))
            if conf_obj.sub_group_by:
                _sgb = conf_obj.sub_group_by
                _sgb_dotted = getattr(conf_obj, 'sub_group_by_is_dotted', False)
                if _sgb_dotted:
                    records = records.filtered(
                        lambda nonz, _s=_sgb: self._get_nested_value(nonz, _s)
                    )
                else:
                    records = records.filtered(lambda nonz, _s=_sgb: getattr(nonz, _s))
        if conf_obj.limit_record > 0:
            records = records[: conf_obj.limit_record]

        for record in records:
            # ── Compute group key(s): M2M partner fields expand into one key per value ──
            if getattr(conf_obj, "group_by_is_dotted", False):
                raw_val = self._get_nested_value(record, conf_obj.group_by)
                if isinstance(raw_val, models.Model):
                    # Many2one → 1 key ; Many2many → 1 key per related record
                    group_keys = [(v.display_name, v.id) for v in raw_val] if raw_val else [(False, False)]
                elif isinstance(raw_val, (date, datetime)) and conf_obj.time_range:
                    lbl = format_date_by_range(raw_val, conf_obj.time_range)
                    group_keys = [(lbl, lbl)]
                else:
                    # Selection: resolve key → label; plain char/bool: use as-is
                    label = self._resolve_partner_selection_label(conf_obj.model, conf_obj.group_by, raw_val)
                    group_keys = [(label if label is not None else raw_val, raw_val)]
            else:
                record_group_by = getattr(record, conf_obj.group_by)
                record_group_id = getattr(record, conf_obj.group_by)
                if hasattr(record._fields[conf_obj.group_by], "selection"):
                    record_selections = record._fields[conf_obj.group_by].selection
                    if isinstance(record_selections, str):
                        record_selections = dict(getattr(record, record_selections)())
                    else:
                        record_selections = dict(record_selections)
                    record_group_by = record_selections.get(getattr(record, conf_obj.group_by))
                    record_group_id = record_selections.get(getattr(record, conf_obj.group_by))
                elif isinstance(record_group_by, models.Model):
                    if len(record_group_by) != 1:
                        # M2M : une clé par valeur liée (ou False si vide)
                        group_keys = [(v.display_name, v.id) for v in record_group_by] if record_group_by else [(False, False)]
                        record_group_by = None  # signal que group_keys est déjà rempli
                    else:
                        record_group_by = record_group_by.display_name
                        record_group_id = record_group_id.id
                elif isinstance(record_group_by, (date, datetime)) and conf_obj.time_range:
                    record_group_by = format_date_by_range(record_group_by, conf_obj.time_range)
                    record_group_id = format_date_by_range(record_group_by, conf_obj.time_range)
                if record_group_by is not None:
                    group_keys = [(record_group_by, record_group_id)]

            # Sub-group by resolved once per record, shared across all group_keys
            sub_groupby = None
            if conf_obj.sub_group_by:
                _sub_dotted = getattr(conf_obj, 'sub_group_by_is_dotted', False)
                if _sub_dotted:
                    raw_sub = self._get_nested_value(record, conf_obj.sub_group_by)
                    if isinstance(raw_sub, models.Model):
                        sub_groupby = raw_sub.display_name if raw_sub else False
                    elif isinstance(raw_sub, (date, datetime)) and conf_obj.sub_time_range:
                        sub_groupby = format_date_by_range(raw_sub, conf_obj.sub_time_range)
                    else:
                        label = self._resolve_partner_selection_label(
                            conf_obj.model, conf_obj.sub_group_by, raw_sub
                        )
                        sub_groupby = label if label is not None else raw_sub
                else:
                    sub_groupby = getattr(record, conf_obj.sub_group_by)
                    if hasattr(record._fields.get(conf_obj.sub_group_by, type('', (), {})()), "selection"):
                        record_selections = record._fields[conf_obj.sub_group_by].selection
                        if isinstance(record_selections, str):
                            record_selections = dict(getattr(record, record_selections)())
                        else:
                            record_selections = dict(record_selections)
                        sub_groupby = record_selections.get(getattr(record, conf_obj.sub_group_by))
                    elif isinstance(sub_groupby, models.Model):
                        sub_groupby = sub_groupby.display_name
                    elif isinstance(sub_groupby, (date, datetime)) and conf_obj.sub_time_range:
                        sub_groupby = format_date_by_range(sub_groupby, conf_obj.sub_time_range)

            # Accumulate for each group key (M2M produces multiple keys per record)
            for record_group_by, record_group_id in group_keys:
                if conf_obj.hide_false_value and not record_group_by:
                    continue
                if conf_obj.sub_group_by:
                    if conf_obj.data_type == "count":
                        grouped_data[(record_group_by, record_group_id)][f"{sub_groupby} - count"] += 1
                    if conf_obj.data_type in ["sum", "average"]:
                        grouped_data, measurement_multiplier_value = self.get_measurement_fields(
                            conf_obj, record, grouped_data,
                            (record_group_by, record_group_id), sub_groupby, measurement_multiplier_value,
                        )
                    if conf_obj.data_type == "count_distinct" and conf_obj.measurement_field_id:
                        mf_name = conf_obj.measurement_field_id.name
                        mf_label = conf_obj.measurement_field_id.field_description
                        val = getattr(record, mf_name)
                        val = val.id if isinstance(val, models.Model) else val
                        distinct_sets[(record_group_by, record_group_id)][f"{sub_groupby} - {mf_label}"].add(val)
                else:
                    if conf_obj.data_type == "count":
                        grouped_data[(record_group_by, record_group_id)][" - count"] += 1
                    if conf_obj.data_type in ["sum", "average"]:
                        grouped_data, measurement_multiplier_value = self.get_measurement_fields(
                            conf_obj, record, grouped_data,
                            (record_group_by, record_group_id), False, measurement_multiplier_value,
                        )
                    if conf_obj.data_type == "count_distinct" and conf_obj.measurement_field_id:
                        mf_name = conf_obj.measurement_field_id.name
                        mf_label = conf_obj.measurement_field_id.field_description
                        val = getattr(record, mf_name)
                        val = val.id if isinstance(val, models.Model) else val
                        distinct_sets[(record_group_by, record_group_id)][f" - {mf_label}"].add(val)

        # Convertir les sets count_distinct en counts numériques
        if conf_obj.data_type == "count_distinct":
            for group_key, series_sets in distinct_sets.items():
                for key, val_set in series_sets.items():
                    grouped_data[group_key][key] = float(len(val_set))

        result = []
        for customer, metrics in grouped_data.items():
            row = {
                "category": customer[0],
                "isSubGroupBy": conf_obj.sub_group_by,
                "record_id": customer[1],
            }
            row.update(metrics)
            if conf_obj.data_type == "average":
                for key, value in row.items():
                    if isinstance(value, list):
                        if len(value) != 0:
                            calc = sum(value) / len(value)
                            if (
                                conf_obj.is_apply_multiplier
                                and measurement_multiplier_value.get(key)
                            ):
                                calc = calc * measurement_multiplier_value.get(key)
                            row.update({key: calc})
                        else:
                            row.update({key: 0})
            result.append(row)

        if not result:
            return {"type": "error", "message": "No Data to display!"}

        value_keys = set()
        for row in result:
            value_keys.update(k for k in row if k not in ("category", "record_id"))
        if conf_obj.chart_type != "bar_chart":
            for row in result:
                for key in value_keys:
                    if key not in row:
                        row[key] = 0.0
        return result

    def check_category_config_type(self, conf_obj, records):
        """
        Check datatype of the conf object
        """
        total = sum(getattr(r, conf_obj.measurement_field_id.name) for r in records)
        category_value = (
            total / len(records) if conf_obj.data_type == "average" and total else total
        )
        if conf_obj.is_apply_multiplier:
            if multiplier := next(
                (
                    m["multiplier"]
                    for m in conf_obj.chart_multiplier_ids
                    if m["field_id"] == conf_obj.measurement_field_id.id
                ),
                None,
            ):
                category_value *= multiplier
        return category_value

    def get_category_value_data(self, conf_obj):
        """
        This function is used in preparing data for following charts
        Funnel Chart
        Pie Chart
        Radar Chart
        """
        check_constraint = self.check_conf_obj(conf_obj, True)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            not getattr(conf_obj, "use_global_date", False)
            and conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        all_records = record_obj.search(domain)

        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not all_records:
            return {"type": "error", "message": "No Data to display!"}

        data_list = []
        if conf_obj.sort_order and conf_obj.sort_field:
            sort_records = self.env[conf_obj.model]
            sort_records |= all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda rc: getattr(rc, conf_obj.sort_field)
                if not isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                else getattr(rc, conf_obj.sort_field).display_name,
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sort_records |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sort_records

        _gb_dotted = getattr(conf_obj, "group_by_is_dotted", False)
        if conf_obj.hide_false_value:
            _gb = conf_obj.group_by
            if _gb_dotted:
                all_records = all_records.filtered(
                    lambda nonz, _gb=_gb: self._get_nested_value(nonz, _gb)
                )
            else:
                all_records = all_records.filtered(
                    lambda nonz: getattr(nonz, conf_obj.group_by)
                )
            if conf_obj.sub_group_by:
                all_records = all_records.filtered(
                    lambda nonz: getattr(nonz, conf_obj.sub_group_by)
                )
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]

        # Pre-expand records: M2M partner fields → one entry per M2M value
        accumulated = defaultdict(list)  # {category_label: [record, ...]}
        accumulated_ids = {}             # {category_label: record_id}
        for rec in all_records:
            if _gb_dotted:
                raw = self._get_nested_value(rec, conf_obj.group_by)
                if isinstance(raw, models.Model):
                    keys = [(v.display_name, v.id) for v in raw] if raw else [(False, False)]
                elif isinstance(raw, (date, datetime)) and conf_obj.time_range:
                    lbl = format_date_by_range(raw, conf_obj.time_range)
                    keys = [(lbl, lbl)]
                else:
                    label = self._resolve_partner_selection_label(conf_obj.model, conf_obj.group_by, raw)
                    keys = [(label if label is not None else raw, raw)]
            else:
                grp = getattr(rec, conf_obj.group_by)
                if not hasattr(rec._fields[conf_obj.group_by], "selection"):
                    rid = grp.id if isinstance(grp, models.Model) else grp
                    lbl = grp.display_name if isinstance(grp, models.Model) else grp
                else:
                    sel = rec._fields[conf_obj.group_by].selection
                    if isinstance(sel, str):
                        sel = dict(getattr(rec, sel)())
                    else:
                        sel = dict(sel)
                    lbl = sel.get(grp, grp)
                    rid = lbl
                keys = [(lbl, rid)]
            for (cat, rid) in keys:
                if conf_obj.hide_false_value and not cat:
                    continue
                accumulated[cat].append(rec)
                accumulated_ids[cat] = rid

        for category_instance, cat_records in accumulated.items():
            category_value = 0
            if conf_obj.data_type == "count":
                category_value = len(cat_records)
            elif conf_obj.data_type in ["sum", "average"]:
                category_value = self.check_category_config_type(conf_obj, cat_records)
            elif conf_obj.data_type == "count_distinct" and conf_obj.measurement_field_id:
                mf_name = conf_obj.measurement_field_id.name
                vals = [getattr(r, mf_name) for r in cat_records]
                if vals and isinstance(vals[0], models.Model):
                    category_value = len({v.id for v in vals if v})
                else:
                    category_value = len({v for v in vals if v is not False and v is not None})
            if conf_obj.is_apply_multiplier and conf_obj.chart_multiplier_ids:
                if conf_obj.data_type in ["sum", "average", "count", "count_distinct"]:
                    category_value *= conf_obj.chart_multiplier_ids[0].get("multiplier")
            data_list.append({
                "category": category_instance,
                "record_id": accumulated_ids.get(category_instance, category_instance),
                "value": category_value,
            })
        if not data_list:
            return {"type": "error", "message": "No Data to display!"}
        return sorted(
            data_list,
            key=lambda data: data.get("value"),
            reverse=conf_obj.sort_order == "desc",
        )

    def get_map_chart_data(self, conf_obj):
        """
        This function is used in preparing data for following charts
        Map Chart
        """
        check_constraint = self.check_conf_obj(conf_obj, True)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

            if (
                start_date
                and end_date
                and start_date.date()
                and end_date.date()
                and start_date.date() != end_date.date()
            ):
                domain.extend(date_domain["domain"])
            else:
                today_date = start_date.date()

        all_records = record_obj.search(domain)
        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not all_records:
            return {"type": "error", "message": "No Data to display!"}

        data_list = []
        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = self.env[conf_obj.model]
            sorted_record |= all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda rc: getattr(rc, conf_obj.sort_field).name
                if isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                else getattr(rc, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]
        if conf_obj.measurement_field_id:
            all_records = sorted(
                all_records,
                key=lambda ao: getattr(ao, conf_obj.measurement_field_id.name),
            )

        for country_id, records in groupby(
            all_records,
            key=lambda rec: getattr(rec, conf_obj.map_group_by).country_id,
        ):
            category_value = 0
            if conf_obj.data_type == "sum":
                total_vals = []
                for record in records:
                    total_vals.append(
                        getattr(record, conf_obj.measurement_field_id.name)
                    )
                category_value = sum(total_vals)
                if conf_obj.is_apply_multiplier:
                    filter_measure = list(
                        filter(
                            lambda measure: measure.get("field_id")
                            == conf_obj.measurement_field_id.id,
                            conf_obj.chart_multiplier_ids,
                        )
                    )
                    if filter_measure:
                        category_value = category_value * filter_measure[0].get(
                            "multiplier"
                        )
            elif conf_obj.data_type == "count":
                category_value = len(records)
            elif conf_obj.data_type == "average":
                total_vals = []
                for record in records:
                    total_vals.append(
                        getattr(record, conf_obj.measurement_field_id.name)
                    )
                if sum(total_vals) != 0:
                    category_value = sum(total_vals) / len(records)
                if conf_obj.is_apply_multiplier:
                    filter_measure = list(
                        filter(
                            lambda measure: measure.get("field_id")
                            == conf_obj.measurement_field_id.id,
                            conf_obj.chart_multiplier_ids,
                        )
                    )
                    if filter_measure:
                        category_value = category_value * filter_measure[0].get(
                            "multiplier"
                        )
            if conf_obj.hide_false_value and (category_value == 0 or not country_id):
                continue
            data_list.append(
                {
                    "id": country_id.code,
                    "name": country_id.name,
                    "value": category_value,
                    "record_id": country_id.id,
                }
            )
        if not data_list:
            return {"type": "error", "message": "No Data to display!"}
        return data_list

    def get_meter_chart_data(self, conf_obj):
        check_constraint = self.check_conf_obj(conf_obj, True)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

            if (
                start_date
                and end_date
                and start_date.date()
                and end_date.date()
                and start_date.date() != end_date.date()
            ):
                domain.extend(date_domain["domain"])
            else:
                today_date = start_date.date()

        all_records = record_obj.search(domain)
        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not all_records:
            return {"type": "error", "message": "No Data to display!"}

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = self.env[conf_obj.model]
            sorted_record |= all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda rc: getattr(rc, conf_obj.sort_field).name
                if isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                else getattr(rc, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]
        if conf_obj.measurement_field_id:
            all_records = sorted(
                all_records,
                key=lambda ao: getattr(ao, conf_obj.measurement_field_id.name),
            )

        total_vals = 0
        if conf_obj.data_type == "sum":
            total_vals_list = []
            for record in all_records:
                total_vals_list.append(
                    getattr(record, conf_obj.measurement_field_id.name)
                )
            total_vals = sum(total_vals_list)
        elif conf_obj.data_type == "average":
            if all_records:
                total_vals_list = []
                for record in all_records:
                    total_vals_list.append(
                        getattr(record, conf_obj.measurement_field_id.name)
                    )
                total_vals = sum(total_vals_list) / len(all_records)
        else:
            total_vals = len(all_records)

        target = conf_obj.meter_target
        if (
            conf_obj.date_filter_option
            not in [
                "none",
                "past_till_now",
                "past_excluding_today",
                "future_starting_now",
                "future_starting_tomorrow",
            ]
            and conf_obj.previous_period_comparision
        ):
            today_date = False
            domain = conf_obj.domain
            if conf_obj.company and "company_id" in record_obj._fields:
                domain.append(("company_id", "in", [conf_obj.company, False]))
            if (
                conf_obj.date_filter_field
                and conf_obj.date_filter_option
                and conf_obj.date_filter_option != "none"
            ):
                date_domain = self.get_date_filter_domain(
                    record_obj,
                    conf_obj.date_filter_field,
                    conf_obj.date_filter_option,
                    conf_obj.include_periods,
                    conf_obj.same_period_previous_years,
                    conf_obj.previous_period_duration,
                )
                if date_domain.get("domain"):
                    start_date = date_domain.get("start_date")
                    end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

            all_records = record_obj.search(domain)
            if today_date:
                all_records = all_records.filtered(
                    lambda record: getattr(record, conf_obj.date_filter_field)
                    and (
                        getattr(record, conf_obj.date_filter_field).date()
                        if isinstance(
                            getattr(record, conf_obj.date_filter_field), datetime
                        )
                        else getattr(record, conf_obj.date_filter_field)
                    )
                    == today_date
                )

            if not all_records:
                return {"type": "error", "message": "Target is not valid!"}

            if conf_obj.sort_order and conf_obj.sort_field:
                sorted_record = self.env[conf_obj.model]
                sorted_record |= all_records.filtered(
                    lambda arft: getattr(arft, conf_obj.sort_field)
                ).sorted(
                    key=lambda rc: getattr(rc, conf_obj.sort_field).name
                    if isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                    else getattr(rc, conf_obj.sort_field),
                    reverse=True if conf_obj.sort_order == "desc" else False,
                )
                sorted_record |= all_records.filtered(
                    lambda arft: not getattr(arft, conf_obj.sort_field)
                )
                all_records = sorted_record
            if conf_obj.limit_record > 0:
                all_records = all_records[: conf_obj.limit_record]
            if conf_obj.measurement_field_id:
                all_records = sorted(
                    all_records,
                    key=lambda ao: getattr(ao, conf_obj.measurement_field_id.name),
                )

            target = 0
            if conf_obj.data_type == "sum":
                target = sum(all_records.mapped(conf_obj.measurement_field_id.name))
            elif conf_obj.data_type == "average":
                if all_records:
                    target_vals_list = []
                    for record in all_records:
                        target_vals_list.append(
                            getattr(record, conf_obj.measurement_field_id.name)
                        )
                    target = sum(target_vals_list) / len(all_records)
            else:
                target = len(all_records)
        if target <= 0:
            return {"type": "error", "message": "Target is not valid!"}
        return {
            "type": "success",
            "current_value": round(total_vals, 2),
            "target": target,
        }

    def get_date_filter_domain(
        self,
        model_obj,
        date_filter_field,
        date_filter_option,
        include_periods=0,
        same_period_previous_years=0,
        previous=0,
    ):
        """
        Prepare date filters domain based on configuration
        """
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        now = datetime.now()

        def start_end(dt, period, delta=relativedelta()):
            if period == "week":
                return dt - timedelta(days=dt.weekday()), dt + timedelta(days=6)
            elif period == "quarter":
                q = (dt.month - 1) // 3
                start = datetime(dt.year, 3 * q + 1, 1)
                return start, start + relativedelta(months=3) - timedelta(days=1)
            return dt.replace(day=1), dt.replace(day=1) + relativedelta(
                months=1
            ) - timedelta(days=1)

        date_ranges = {
            "today": (
                today - timedelta(days=previous),
                today - timedelta(days=previous),
            ),
            "this_week": start_end(today - relativedelta(weeks=previous), "week"),
            "this_month": start_end(today - relativedelta(months=previous), "month"),
            "this_quarter": start_end(
                today - relativedelta(months=previous * 3), "quarter"
            ),
            "this_year": (
                datetime(today.year - previous, 1, 1),
                datetime(today.year - previous, 12, 31),
            ),
            "week_to_date": (
                start_end(today - relativedelta(weeks=previous), "week")[0],
                today - relativedelta(weeks=previous),
            ),
            "month_to_date": (
                today.replace(day=1) - relativedelta(months=previous),
                today - relativedelta(months=previous),
            ),
            "quarter_to_date": (
                start_end(today - relativedelta(months=previous * 3), "quarter")[0],
                today,
            ),
            "year_to_date": (
                datetime(today.year - previous, 1, 1),
                today - relativedelta(years=previous),
            ),
            "next_day": (
                today - relativedelta(days=previous) + timedelta(days=1),
                today - relativedelta(days=previous) + timedelta(days=1),
            ),  # * 2
            "next_week": (
                start_end(today - relativedelta(weeks=previous), "week")[0]
                + timedelta(weeks=1),
                start_end(today - relativedelta(weeks=previous), "week")[1]
                + timedelta(weeks=1),
            ),
            "next_month": (
                start_end(today - relativedelta(months=previous), "month")[0]
                + relativedelta(months=1),
                start_end(today - relativedelta(months=previous), "month")[1]
                + relativedelta(months=1),
            ),
            "next_quarter": (
                start_end(today, "quarter")[0] + relativedelta(months=3),
                start_end(today, "quarter")[1] + relativedelta(months=3),
            ),
            "next_year": (
                datetime(today.year - previous + 1, 1, 1),
                datetime(today.year - previous + 1, 12, 31),
            ),
            "last_day": (
                today - relativedelta(days=previous) - timedelta(days=1),
                today - relativedelta(days=previous) - timedelta(days=1),
            ),  # * 2
            "last_week": (
                start_end(today - relativedelta(weeks=previous), "week")[0]
                - timedelta(weeks=1),
                start_end(today - relativedelta(weeks=previous), "week")[1]
                - timedelta(weeks=1),
            ),
            "last_month": (
                start_end(
                    today - relativedelta(months=previous) - relativedelta(months=1),
                    "month",
                )[0],
                start_end(
                    today - relativedelta(months=previous) - relativedelta(months=1),
                    "month",
                )[1],
            ),
            "last_quarter": (
                start_end(
                    today
                    - relativedelta(months=previous * 3)
                    - relativedelta(months=3),
                    "quarter",
                )[0],
                start_end(
                    today
                    - relativedelta(months=previous * 3)
                    - relativedelta(months=3),
                    "quarter",
                )[1],
            ),
            "last_year": (
                datetime(today.year - previous - 1, 1, 1),
                datetime(today.year - previous - 1, 12, 31),
            ),
            "last_seven_days": (
                today - relativedelta(days=7 * previous) - timedelta(days=7),
                today - relativedelta(days=7 * previous) - timedelta(seconds=1),
            ),
            "last_thirty_days": (
                today - relativedelta(days=30 * previous) - timedelta(days=30),
                today - relativedelta(days=30 * previous) - timedelta(seconds=1),
            ),
            "last_ninety_days": (
                today - relativedelta(days=90 * previous) - timedelta(days=90),
                today - relativedelta(days=90 * previous) - timedelta(seconds=1),
            ),
            "last_year_days": (
                today - relativedelta(years=previous) - timedelta(days=365),
                today - relativedelta(years=previous) - timedelta(seconds=1),
            ),
            "past_till_now": (datetime.min, now),
            "past_excluding_today": (datetime.min, today - timedelta(seconds=1)),
            "future_starting_today": (today, datetime.max),
            "future_starting_now": (now, datetime.max),
            "future_starting_tomorrow": (today + timedelta(days=1), datetime.max),
        }

        if date_filter_option not in date_ranges:
            return {"domain": [], "start_date": False, "end_date": False}

        base_start, base_end = date_ranges[date_filter_option]
        if include_periods > 0:
            base_end += (base_end - base_start) * include_periods

        domain = [
            (date_filter_field, ">=", base_start),
            (date_filter_field, "<=", base_end),
        ]
        for i in range(1, same_period_previous_years + 1):
            domain += [
                "|",
                (date_filter_field, ">=", base_start.replace(year=base_start.year - i)),
                (date_filter_field, "<=", base_end.replace(year=base_end.year - i)),
            ]
        return {
            "domain": domain,
            "start_date": base_start,
            "end_date": base_end.replace(
                hour=23, minute=59, second=59, microsecond=999999
            ),
        }


class ItemViewAction(models.Model):
    _name = "item.view.action"
    _description = "Item View Action"

    chart_id = fields.Many2one("dashboard.chart", string="Chart", ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", related="chart_id.model_id")
    group_by_id = fields.Many2one(
        "ir.model.fields", string="Action Group By", required=True, ondelete="cascade"
    )
    sort_field_id = fields.Many2one("ir.model.fields", string="Sort With")
    sort_order = fields.Selection(
        [("asc", "Ascending"), ("desc", "Descending")], string="Sort Order"
    )
    limit_record = fields.Integer(string="Record Limit", default=0)
    chart_type = fields.Selection(
        [
            ("bar_chart", "Bar Chart"),
            ("column_chart", "Column Chart"),
            ("doughnut_chart", "Doughnut Chart"),
            ("area_chart", "Area Chart"),
            ("funnel_chart", "Funnel Chart"),
            ("pyramid_chart", "Pyramid Chart"),
            ("line_chart", "Line Chart"),
            ("pie_chart", "Pie Chart"),
            ("radar_chart", "Radar Chart"),
            ("stackedcolumn_chart", "StackedColumn Chart"),
            ("radial_chart", "Radial Chart"),
            ("scatter_chart", "Scatter Chart"),
        ],
        default="bar_chart",
        required=True,
        string="Type",
    )

    @api.constrains("limit_record")
    def _check_limit_record(self):
        for item in self:
            if item.limit_record and item.limit_record < 0:
                raise ValidationError(
                    _(
                        "Oops! The record limit can’t be less than zero. Please enter a value of zero or higher to continue."
                    )
                )


class ChartMultiplier(models.Model):
    _name = "chart.multiplier"
    _description = "Chart Multiplier"

    chart_id = fields.Many2one("dashboard.chart", string="Chart", ondelete="cascade")
    field_id = fields.Many2one("ir.model.fields", string="Multiplier field")
    multiplier = fields.Float(string="Multiplier", default=1.0)

    @api.constrains("multiplier")
    def _check_limit_multiplier(self):
        for rec in self:
            if rec.multiplier and rec.multiplier < 0:
                raise ValidationError(
                    _(
                        "The multiplier must be 1 or greater. Please enter a valid value to proceed."
                    )
                )

    @api.onchange("multiplier")
    def _onchange_multiplier(self):
        if self.multiplier and self.multiplier < 0:
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "The multiplier must be 1 or greater. Please enter a valid value to proceed."
                    ),
                }
            }
