# Archive Index — 2026-03

| Feature | Phase | Match Rate | Archived At | Path |
|---------|:-----:|:----------:|-------------|------|
| locky-agent | completed | 93% | 2026-03-24 | [locky-agent/](./locky-agent/) |
| locky-agent-v1.1 | completed | 95% | 2026-03-25 | [locky-agent-v1.1/](./locky-agent-v1.1/) |
| jira-integration | completed | 95% | 2026-03-25 | [jira-integration/](./jira-integration/) |
| locky-v2-overhaul | completed | 97% | 2026-03-25 | [locky-v2-overhaul/](./locky-v2-overhaul/) |

## locky-agent-v1.1 요약

- **버전**: v1.0.0 → v1.1.0
- **기간**: 2026-03-24~25
- **구현**: REPL 컨텍스트, 대화형 init, locky update, config.yaml
- **테스트**: 167개 테스트 pass
- **Match Rate**: 95%

## jira-integration 요약

- **버전**: v1.1.0 + jira feature
- **기간**: 2026-03-25
- **구현**: tools/jira_client.py, actions/jira.py, 3개 CLI 명령 (list/create/status)
- **테스트**: 26개 신규 테스트 (167+26=193개)
- **Match Rate**: 95%, Plan Success 7/7 달성
- **보안**: _sanitize_result() 추가

## locky-v2-overhaul 요약

- **버전**: v1.1.0 → v2.0.0
- **기간**: 2026-03-25
- **구현**: locky/ 패키지 신규 (Core + Tools + Agents + Runtime 4계층), CLI ask/edit/agent 명령, REPL /ask /edit
- **테스트**: 70개 신규 (전체 263개)
- **Match Rate**: 97% (1회 이터레이션)

## locky-agent 요약

- **버전**: v0.3.0 → v1.0.0
- **기간**: 2026-03-24 (단일 세션)
- **구현**: 6개 신규 모듈 (context, lang_detect, hook, pipeline, format_code, ollama_guard)
- **테스트**: 132개 테스트 pass
- **CLI**: 11개 서브커맨드
- **FR 완료율**: 11/13 Done, 2 Partial
