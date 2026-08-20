# Docker — Odoo local

## Inicio rápido

```bash
docker compose up --build -d
docker compose logs -f odoo
```

Abrir http://localhost:8069 — login `admin` / `admin`, base de datos `ragnar`.

## Requisitos (Windows)

1. **Virtualización** activada en BIOS/UEFI (Intel VT-x / AMD-V)
2. **WSL2** instalado (`wsl --install --no-distribution`)
3. **Reinicio** del sistema tras instalar WSL
4. **Docker Desktop** en ejecución

PowerShell:

```powershell
.\scripts\docker-up.ps1
```

## Si Docker no arranca

Mensajes típicos:

- `WSL2 is unable to start since virtualization is not enabled` → activar virtualización en BIOS y reiniciar
- `Changes will not be effective until the system is rebooted` → reiniciar Windows

Comprobar:

```powershell
wsl --status
docker info
```

## Alternativa sin Docker

```bash
python scripts/run_mock_demo.py          # lógica de los 3 flujos
cd docs/mockup && python -m http.server 8765   # UI demo
```

## Detener

```bash
docker compose down
```

Para borrar datos: `docker compose down -v`
