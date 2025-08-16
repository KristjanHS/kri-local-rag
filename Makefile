setup-hooks:
	@echo "Configuring Git hooks path..."
	@git config core.hooksPath scripts/git-hooks
	@echo "Done."

.PHONY: setup-hooks
