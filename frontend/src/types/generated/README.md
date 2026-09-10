# 생성된 타입 (손으로 고치지 마세요)

권위 정의: `backend/src/itb/domain/*.py` (Pydantic v2). 헌법 Cross-language schema duty.

재생성:

```bash
cd backend && uv run python -m itb.schema.export
cd ../frontend && npm run gen:types
```

배럴 파일을 두지 않는다 — 스키마마다 생성되는 별칭 타입(`Name`, `Label`, `Tab` 등)이
한곳에 모이면 이름이 충돌한다. 파일을 직접 임포트한다.

## 파일

- `draft.d.ts`
- `error-response.d.ts`
- `manual-step.d.ts`
- `project.d.ts`
- `run-result.d.ts`
- `step-dsl.d.ts`
- `step.d.ts`
