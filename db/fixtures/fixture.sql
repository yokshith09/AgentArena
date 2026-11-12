-- FABRICATED TEST DATA (07 section 9). Never present as results.
INSERT INTO agents(agent_id,name,mode,entrypoint,model_config,source_path) VALUES
 ('agent-a-plain','agent-a-plain','command','python agent.py','{"model":"mock-model"}','agents/agent_a'),
 ('agent-b-fw','agent-b-fw','command','python agent.py','{"model":"mock-model"}','agents/agent_b');
INSERT INTO tasks(task_id,category,prompt,workspace,grader,reference_solution,faults_allowed,task_dir,task_hash,validated) VALUES
 ('fix-off-by-one','coding','Fix the bug','workspace','{"type":"pytest","config":{}}','reference_solution','{provider_503_outage}','tasks/fix-off-by-one','h1',true);
INSERT INTO benchmarks(benchmark_id,name,config,state) VALUES
 ('11111111-1111-4111-8111-111111111111','fixture','{"n_runs":1}','completed');
INSERT INTO runs(run_id,agent_id,task_id,scenario,model,status,passed,tokens_in,tokens_out,cost,cost_confidence,duration,steps,benchmark_id,state,tool_calls) VALUES
 ('22222222-2222-4222-8222-222222222222','agent-a-plain','fix-off-by-one','provider_503_outage','mock-model','PASS',true,1200,300,0.0042,'verified',37.5,6,'11111111-1111-4111-8111-111111111111','done',8),
 ('33333333-3333-4333-8333-333333333333','agent-b-fw','fix-off-by-one','baseline',NULL,'INFRA_ERROR',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'11111111-1111-4111-8111-111111111111','done',NULL);
INSERT INTO events(run_id,type,payload,latency,error) VALUES
 ('22222222-2222-4222-8222-222222222222','fault_injected','{"fault_id":"provider_503_outage","group":"provider","detail":"call 1 of 3"}',NULL,NULL),
 ('22222222-2222-4222-8222-222222222222','llm_call','{"endpoint":"/chat/completions","status_code":503}',4,'injected'),
 ('22222222-2222-4222-8222-222222222222','llm_call','{"endpoint":"/chat/completions","status_code":200,"tokens_in":400,"tokens_out":90,"cost":0.0012,"cost_confidence":"verified"}',2100,NULL),
 ('22222222-2222-4222-8222-222222222222','tool_call','{"name":"run_tests","call_id":"c1"}',NULL,NULL);
