.PHONY: sync-atlas check-atlas

sync-atlas:
	git submodule update --init vendor/license.atlas
	python scripts/sync_license_atlas.py

check-atlas:
	python scripts/sync_license_atlas.py --check-only

.PHONY: e2b:build:dev
e2b:build:dev:
	python build_dev.py

.PHONY: e2b:build:prod
e2b:build:prod:
	python build_prod.py
