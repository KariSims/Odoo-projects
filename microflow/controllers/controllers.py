# -*- coding: utf-8 -*-
import os
from odoo import http
from odoo.http import request, Response


class MicroflowController(http.Controller):

    @http.route('/microflow/sw.js', auth='public', type='http', csrf=False)
    def service_worker(self, **kw):
        sw_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'src', 'js', 'service_worker.js'
        )
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(
            content,
            headers={
                'Content-Type': 'application/javascript',
                'Service-Worker-Allowed': '/',
                'Cache-Control': 'no-cache',
            }
        )
