#!/bin/bash
set -e

DB_NAME="${DB_NAME:-ragnar}"
MARKER="/var/lib/odoo/.db_initialized_${DB_NAME}"

echo "[entrypoint] Waiting for PostgreSQL..."
python3 - <<'PY'
import os, time, psycopg2
host=os.environ.get("HOST","db"); user=os.environ.get("USER","odoo"); password=os.environ.get("PASSWORD","odoo")
for i in range(60):
    try:
        psycopg2.connect(host=host,user=user,password=password,dbname="postgres").close()
        print("[entrypoint] PostgreSQL ready"); break
    except Exception as e:
        if i==59: raise SystemExit(e)
        time.sleep(2)
PY

rm -rf /var/lib/odoo/sessions/* 2>/dev/null || true
mkdir -p /var/lib/odoo/sessions

if [ ! -f "${MARKER}" ]; then
  echo "[entrypoint] Installing fresh DB + module..."
  odoo -c /etc/odoo/odoo.conf -d "${DB_NAME}" \
    -i ragnar_whatsapp_integration \
    --without-demo=False \
    --stop-after-init

  echo "[entrypoint] Setting admin/admin and locking signup..."
  odoo shell -c /etc/odoo/odoo.conf -d "${DB_NAME}" --no-http <<'PY'
admin = env['res.users'].sudo().browse(2)
admin.write({
    'login': 'admin',
    'password': 'admin',
    'name': 'Administrator',
})
ICP = env['ir.config_parameter'].sudo()
ICP.set_param('auth_signup.invitation_scope', 'b2b')
ICP.set_param('auth_signup.reset_password', 'False')
# Kill any portal users
env['res.users'].sudo().search([('share', '=', True), ('active', '=', True)]).write({'active': False})
env.cr.commit()
print('LOGIN=admin PASSWORD=admin')
PY
  touch "${MARKER}"
  echo "[entrypoint] Init complete."
fi

echo "[entrypoint] Odoo ready at :8069  |  login=admin  password=admin"
exec odoo -c /etc/odoo/odoo.conf -d "${DB_NAME}"
