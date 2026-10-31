# Render deployment

This Blueprint runs `TrendRider` as a Docker background worker in dry-run mode.
It does not place real orders, expose the Freqtrade API, or require exchange API
keys. The SQLite database and log are stored on a Render persistent disk.

## Deploy

1. Push this repository to a Git provider connected to Render.
2. In Render, create a new Blueprint from that repository and review the
   `freqtrade-trendrider` worker and its persistent-disk cost before applying.
3. Check the worker logs after deployment to confirm the bot starts in dry-run.

Render persistent disks require a paid service plan. Verify current pricing in
the Render dashboard before creating the service.

Do not replace `deployment/freqtrade-render.json` with a local config file or
add exchange keys, API passwords, or JWT secrets to this repository. Keep
`dry_run` set to `true` unless a separately reviewed live-trading deployment is
explicitly intended.
