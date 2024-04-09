# refinance
refined finance system.

## develop
```
pipenv install --dev
pipenv shell
pytest
uvicorn refinance.app:app --reload
```

## todo
- [x] base classes
- [x] errors
- [x] unit tests
- [x] complex search
- [x] pagination
- [x] tags
- [ ] transactions
- [ ] recurrent payments
- [ ] migrations (not alembic)
- [ ] logging
- [ ] docker
- [ ] grafana, statistics
