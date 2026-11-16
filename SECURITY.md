# Seguridad

## Cómo avisar de un fallo

**No abras un issue público.** Usa [«Report a vulnerability»](https://github.com/Oda615/MiTallercito/security/advisories/new) (aviso privado de GitHub). Cuenta qué versión usas, cómo reproducirlo y qué impacto tiene. Respondemos en cuanto podamos y te damos crédito en la nota de la versión si quieres.

## Modelo de amenazas (resumen)

| Pieza | Corre como | Qué puede tocar |
|---|---|---|
| Web (gunicorn) | usuario `mitallercito` sin privilegios, `NoNewPrivileges`, `ProtectSystem=full` | `/var/lib/mitallercito` (BD, archivos, copias) |
| Aplicador de actualizaciones | root, lanzado por `mitallercito-update.path` | copia ficheros de la app a `/opt/mitallercito`, reinicia el servicio |
| Verificador `/usr/local/lib/mitallercito/verify.py` y clave `/etc/mitallercito/signing.pub` | root | solo los cambia el instalador del host, **nunca** la web |
| Puente | usuario `mitallercito-bridge`, `ProtectSystem=strict` | habla con Moonraker en su LAN y con la tienda por HTTPS saliente |

Decisiones:
- **Primer arranque** protegido por un código de un solo uso (`mitallercito setup-token`) que se borra al crear el administrador.
- **Paquetes de actualización**: firma Ed25519 sobre el `payload.tar.gz`; solo se aceptan ficheros regulares y carpetas dentro de `mitallercito/` de una lista cerrada; nada del paquete se ejecuta como root; las dependencias se instalan como el usuario sin privilegios; copia de la BD y vuelta atrás automática.
- El canal **main** no va firmado: solo se permite en instalaciones sin clave pública (o con `MT_ALLOW_UNSIGNED=1`).
- **Login**: hash scrypt (werkzeug), 5 intentos fallidos por IP cada 15 min, cookie `HttpOnly`/`SameSite=Lax` y `Secure` bajo HTTPS. IP real tras proxy con `MT_PROXY_HOPS`.
- **Subidas**: imágenes validadas por firma de fichero (sin SVG); se sirven con `Content-Security-Policy: sandbox`. Los modelos se descargan siempre como adjunto.
- **Impresoras**: las API keys no se devuelven al navegador; los tokens de puente se guardan como SHA-256.

## Versiones con soporte
Solo la última versión publicada.
