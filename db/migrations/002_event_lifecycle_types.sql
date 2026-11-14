-- 002_event_lifecycle_types.sql: add orchestrator lifecycle/grader event types.
-- Contract change proposed by Dev-C on 2026-11-13 (docs/07 section 3, docs/10 section 2.5),
-- accepted by DEV-A on 2026-11-14. Additive: every existing event type stays valid.
--   agent_started  payload {task_id}             written by the orchestrator after state='running'
--   grader_result  payload {passed, suite_count} written by the orchestrator after grading
ALTER TABLE events DROP CONSTRAINT events_type_check;
ALTER TABLE events ADD CONSTRAINT events_type_check CHECK (type IN (
  'agent_started', 'llm_call', 'tool_call', 'grader_result',
  'command', 'file_write', 'net_attempt', 'fault_injected'));
