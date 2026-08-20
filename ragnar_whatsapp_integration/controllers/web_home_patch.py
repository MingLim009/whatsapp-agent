# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.utils import is_user_internal, ensure_db
from odoo.service import security
import odoo


class HomePatch(Home):
    """Stop /web redirect loops caused by portal/public sessions."""

    @http.route('/web', type='http', auth='none')
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if not request.session.uid:
            return request.redirect('/web/login?db=ragnar', 303)
        if not security.check_session(request.session, request.env):
            request.session.logout(keep_db=True)
            return request.redirect('/web/login?db=ragnar', 303)
        if not is_user_internal(request.session.uid):
            # Portal users cannot use backend; wipe session instead of dead-end page
            request.session.logout(keep_db=True)
            return request.redirect('/web/login?db=ragnar&message=Use+admin+account', 303)

        request.session.touch()
        request.update_env(user=request.session.uid)
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except Exception:
            request.session.logout(keep_db=True)
            return request.redirect('/web/login?db=ragnar&error=access', 303)

    @http.route('/web/login_successful', type='http', auth='user', sitemap=False)
    def login_successful_external_user(self, **kwargs):
        # Never leave users on the dead-end page
        request.session.logout(keep_db=True)
        return request.redirect('/web/login?db=ragnar', 303)
