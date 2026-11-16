# Puente de impresoras / Printer bridge

Para impresoras que están en **otra red** que el servidor de MiTallercito (otra casa, otro taller, el servidor en un VPS…).

```
 [Impresoras Klipper]  ←LAN→  [puente]  ──HTTPS saliente──►  [MiTallercito]
   192.168.1.x                Raspberry Pi                     tienda.midominio.com
```

- El puente solo hace conexiones **hacia fuera**: no hay que abrir puertos ni montar VPN.
- La configuración (qué impresoras, su IP local y su API key) se hace en la web; el puente la descarga.
- Cada 10 s envía el estado; cada minuto, el historial de impresiones. Recoge los G-code que mandéis desde un pedido y los sube a la impresora.
- Solo necesita Python 3.9+ (sin dependencias).

## Instalar
1. En la web: **Ajustes → Puentes → Crear puente**. Copia el comando (el token solo se muestra una vez).
2. En un equipo Linux siempre encendido de la red de las impresoras:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/bridge/install-bridge.sh | \
     sudo bash -s -- --url https://tienda.midominio.com --token mtb_…
   ```
3. En **Ajustes → Impresoras**, en cada impresora de esa red: *Conexión = Puente*, elige el puente y pon su IP local.

Logs: `journalctl -u mitallercito-bridge -f` · Config: `/etc/mitallercito-bridge.env`

## Seguridad
- Usa `https://` en `MT_URL`: el token viaja en cada petición.
- El token solo da acceso a la API del puente (su configuración, informar estado y descargar los G-code que se le encarguen); no sirve para entrar en la web. Si se pierde, borra el puente en la web y crea otro.
- El servicio corre con un usuario sin privilegios y `ProtectSystem=strict`.

## Sin instalar (pruebas)
```bash
MT_URL=https://tienda.midominio.com BRIDGE_TOKEN=mtb_… python3 mitallercito-bridge.py --once
```
