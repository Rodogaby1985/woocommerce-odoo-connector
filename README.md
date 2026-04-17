# Conector WooCommerce ↔ Odoo

Conector bidireccional en tiempo real para sincronizar **productos, stock, precios, pedidos, clientes y categorías** entre WooCommerce y Odoo.

## Arquitectura

```text
WooCommerce --(webhooks)--> Flask Middleware --(Celery/Redis)--> Workers --> Odoo (XML-RPC o JSON-RPC /json/2)
     ^                                                                                       |
     |------------------------------(eventos desde Odoo Automated Actions)-------------------|
```

- **Middleware**: Flask + Celery
- **Broker**: Redis
- **Entrada WooCommerce**: `POST /webhook/woocommerce`
- **Entrada Odoo**: `POST /webhook/odoo`

## Entidades sincronizadas

| Entidad | Woo → Odoo | Odoo → Woo |
|---|---:|---:|
| Productos | ✅ | ✅ |
| Stock | ✅ (en producto) | ✅ |
| Precios | ✅ | ✅ |
| Pedidos | ✅ | ✅ (estado/stock vía tareas) |
| Clientes | ✅ | ✅ |
| Categorías | ✅ | ✅ |

## Requisitos previos

- Python 3.11+
- Redis 7+
- Instancia de WooCommerce con API REST habilitada
- Instancia de Odoo con acceso XML-RPC (14-18) o JSON-RPC `/json/2` (19+)

## Instalación local

1. Clonar repositorio.
2. Crear entorno virtual e instalar dependencias:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copiar variables:
   ```bash
   cp .env.example .env
   ```
4. Ejecutar Flask:
   ```bash
   gunicorn -w 2 -b 0.0.0.0:8000 connector.webhook_server:app
   ```
5. Ejecutar worker Celery:
   ```bash
   celery -A connector.tasks.celery_app worker --loglevel=info
   ```

## Instalación con Docker

```bash
docker compose up --build
```

Servicios:
- `redis`
- `middleware`
- `worker`

## Variables de entorno

Ver `.env.example`.

Campos clave:
- `WC_URL`, `WC_CONSUMER_KEY`, `WC_CONSUMER_SECRET`
- `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`
- `ODOO_API_KEY`, `ODOO_PROTOCOL`, `ODOO_VERSION`
- `PRICE_STRATEGY`, `ODOO_SALE_PRICELIST_ID`
- `WEBHOOK_SECRET`
- `CELERY_BROKER`

## Compatibilidad de versiones de Odoo

| Versión Odoo | Protocolo soportado | Recomendación |
|---|---|---|
| 14-18 | XML-RPC (`/xmlrpc/2`) | Usar `ODOO_PROTOCOL=xmlrpc` o `auto` sin API key |
| 19+ | JSON-RPC (`/json/2`) + XML-RPC legacy | Preferir `ODOO_PROTOCOL=jsonrpc` o `auto` con `ODOO_API_KEY` |

## Configuración para Odoo 19+

1. Generar API key en Odoo (Preferencias de usuario).
2. Configurar:
   - `ODOO_PROTOCOL=auto` (o `jsonrpc`)
   - `ODOO_API_KEY=<tu_api_key>`
   - `ODOO_VERSION=19`

## Precios oferta / descuento

Mapeo principal:
- WooCommerce `regular_price` ↔ Odoo `list_price`
- WooCommerce `sale_price` ↔ Odoo `x_sale_price`
- WooCommerce `date_on_sale_from` ↔ Odoo `x_sale_date_from`
- WooCommerce `date_on_sale_to` ↔ Odoo `x_sale_date_to`

Campos personalizados recomendados en `product.template`:
- `x_sale_price` (Float)
- `x_sale_date_from` (Datetime/Date)
- `x_sale_date_to` (Datetime/Date)

### Estrategia de precios

- `PRICE_STRATEGY=custom_fields` (default): usa campos `x_sale_*`.
- `PRICE_STRATEGY=pricelist`: usa `product.pricelist.item` y requiere `ODOO_SALE_PRICELIST_ID`.

## Configuración de webhooks en WooCommerce

Configurar webhooks apuntando a:
- `https://TU_MIDDLEWARE/webhook/woocommerce`

Topics soportados:
- `product.created`, `product.updated`, `product.restored`
- `order.created`, `order.updated`
- `customer.created`, `customer.updated`

La firma se valida con `X-WC-Webhook-Signature` (HMAC-SHA256 + Base64).

## Configuración de Automated Actions en Odoo

Crear acciones automáticas para:
- Productos (`product.template`) usando `odoo_actions/product_action.py`
- Stock (`stock.quant`) usando `odoo_actions/stock_action.py`

Endpoint destino:
- `https://TU_MIDDLEWARE/webhook/odoo`

Eventos soportados:
- `product.write`
- `variant.write`
- `stock.change`

## Campo personalizado `x_wc_id` en Odoo

Se recomienda crear el campo técnico `x_wc_id` en `product.template` y `res.partner` para rastrear el ID remoto de WooCommerce y evitar duplicados.

## Soporte de productos variables (variantes)

El conector soporta sincronización bidireccional de productos variables:

- WooCommerce `attributes[]` → `product.attribute` + `product.attribute.value`
- WooCommerce producto padre `type=variable` ↔ `product.template`
- WooCommerce `/products/{id}/variations` ↔ `product.product`

Campos técnicos recomendados en Odoo:
- `x_wc_id` en `product.template`
- `x_wc_variation_id` en `product.product`

### Flujo WooCommerce → Odoo

1. Se recibe `product.created` / `product.updated` para producto variable.
2. Se sincroniza plantilla y líneas de atributos.
3. Se consultan variaciones y se crean/actualizan variantes individuales con SKU, precio y stock.

### Flujo Odoo → WooCommerce

1. Cambios en `product.template` con variantes se sincronizan como `type=variable`.
2. Se sincronizan atributos del template.
3. Cada `product.product` crea/actualiza su variación remota con stock y precio individual.

## Prevención de bucles

`connector/loop_prevention.py` usa Redis para bloquear ecos recientes con un cooldown configurable (por defecto 30s).

## Mejores prácticas

- Usar HTTPS en todos los endpoints.
- Rotar secrets periódicamente.
- Monitorear logs de Celery y Flask.
- Agregar colas separadas por tipo de entidad cuando haya alto volumen.

## Troubleshooting

- **401 en webhook de WooCommerce**: verificar `WEBHOOK_SECRET` y firma.
- **Eventos no procesados**: revisar que Celery worker esté levantado.
- **Errores XML-RPC**: validar credenciales y permisos de modelos en Odoo.
- **Loops de sincronización**: revisar conectividad a Redis y TTL de claves.
