FROM odoo:17.0

USER root

RUN pip3 install --no-cache-dir --break-system-packages requests 2>/dev/null \
    || pip3 install --no-cache-dir requests

COPY docker/odoo.conf /etc/odoo/odoo.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh /etc/odoo/odoo.conf \
    && chmod +x /entrypoint.sh \
    && chown odoo:odoo /etc/odoo/odoo.conf /entrypoint.sh

USER odoo

ENTRYPOINT ["/entrypoint.sh"]
