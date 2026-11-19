#!/usr/init/env python3
"""
Generador del Banco de Pruebas v2.3 Extendido a 40 Núcleos para HEKT-NOVA.
Construye un dataset basado en 40 núcleos técnicos únicos (2 por dominio),
garantizando paridad lingüística real (ES/EN) y cero relleno sintético.
"""

import json
import os

CASOS_NUCLEO = [
    # --- DOMINIO 1: CIBERSEGURIDAD ([H::SEC]) ---
    {
        "id": "HEKT-CORE-001", "domain": "cybersecurity", "symbolic_namespace": "[H::SEC]", "complexity": 2, "language_parity": ["es"], "task_type": "incident_analysis",
        "raw_prompt": "Detecté múltiples intentos fallidos de autenticación SSH desde la IP 192.168.1.45 contra la cuenta root en los últimos 4 minutos. ¿Qué acciones inmediatas recomiendas?",
        "compressed_payload": "[H::SEC] INCIDENT ssh_bruteforce src=192.168.1.45 target=root window=4m → actions=[drop, alert_secops, ban_temp]"
    },
    {
        "id": "HEKT-CORE-002", "domain": "cybersecurity", "symbolic_namespace": "[H::SEC]", "complexity": 3, "language_parity": ["en"], "task_type": "malware_containment",
        "raw_prompt": "An endpoint running process ID 4412 is establishing outbound TCP connections to a known command and control server at 203.0.113.50. Isolate the host and preserve forensic memory dump.",
        "compressed_payload": "[H::SEC] CONTAIN pid=4412 c2_ip=203.0.113.50 → actions=[isolate_host, memory_dump, alert_soc]"
    },
    # --- DOMINIO 2: ARQUITECTURA DE SOFTWARE ([H::ARCH]) ---
    {
        "id": "HEKT-CORE-003", "domain": "software_architecture", "symbolic_namespace": "[H::ARCH]", "complexity": 3, "language_parity": ["es"], "task_type": "system_design",
        "raw_prompt": "Necesito diseñar el servicio de usuarios con PostgreSQL y Redis. Prefiero el patrón Repository y que las dependencias se inyecten.",
        "compressed_payload": "[H::ARCH] MODULE UserService deps=[PostgresPool, RedisSessionCache] pattern=Repository+DI"
    },
    {
        "id": "HEKT-CORE-004", "domain": "software_architecture", "symbolic_namespace": "[H::ARCH]", "complexity": 3, "language_parity": ["en"], "task_type": "microservices_refactor",
        "raw_prompt": "Decompose the monolith billing module into an independent event-driven microservice communicating via gRPC and Kafka.",
        "compressed_payload": "[H::ARCH] REFACTOR module=billing target=microservice protocol=gRPC broker=Kafka"
    },
    # --- DOMINIO 3: LÓGICA FORMAL ([H::LOGIC]) ---
    {
        "id": "HEKT-CORE-005", "domain": "symbolic_logic", "symbolic_namespace": "[H::LOGIC]", "complexity": 3, "language_parity": ["en"], "task_type": "formal_proof",
        "raw_prompt": "Given premises: If A then B, if B then not C, and C or D. Prove that A implies D using classical logic.",
        "compressed_payload": "[H::LOGIC] PROVE A→D FROM {A→B, B→¬C, C∨D} system=classical"
    },
    {
        "id": "HEKT-CORE-006", "domain": "symbolic_logic", "symbolic_namespace": "[H::LOGIC]", "complexity": 3, "language_parity": ["es"], "task_type": "modal_logic",
        "raw_prompt": "Evalúa si la proposición □P → ◊P es válida en los sistemas modales de Kripke T, S4 y S5.",
        "compressed_payload": "[H::LOGIC] EVALUATE □P→◊P systems=[Kripke_T, S4, S5] check=validity"
    },
    # --- DOMINIO 4: MACHINE LEARNING ([H::ML]) ---
    {
        "id": "HEKT-CORE-007", "domain": "machine_learning", "symbolic_namespace": "[H::ML]", "complexity": 2, "language_parity": ["es"], "task_type": "model_monitoring",
        "raw_prompt": "Tengo un modelo XGBoost para fidelidad semántica. Monitorea drift de features y latencia p99 en producción.",
        "compressed_payload": "[H::ML] MODEL XGBoost target=fidelity monitor=[drift, latency_p99]"
    },
    {
        "id": "HEKT-CORE-008", "domain": "machine_learning", "symbolic_namespace": "[H::ML]", "complexity": 3, "language_parity": ["en"], "task_type": "llm_quantization",
        "raw_prompt": "Quantize a 7B parameter LLM to GGUF Q4_K_M format for local CPU inference via Ollama maintaining perplexity delta < 0.05.",
        "compressed_payload": "[H::ML] QUANTIZE model=7B target=GGUF_Q4_K_M runtime=Ollama max_perplexity_delta=0.05"
    },
    # --- DOMINIO 5: BASES DE DATOS ([H::DB]) ---
    {
        "id": "HEKT-CORE-009", "domain": "database", "symbolic_namespace": "[H::DB]", "complexity": 2, "language_parity": ["en"], "task_type": "query_optimization",
        "raw_prompt": "This query filtering by status and created_at joining users is slow. We need it under 80ms p95.",
        "compressed_payload": "[H::DB] OPTIMIZE query=filter+join target_p95=80ms suggest=indexes"
    },
    {
        "id": "HEKT-CORE-010", "domain": "database", "symbolic_namespace": "[H::DB]", "complexity": 3, "language_parity": ["es"], "task_type": "sharding_strategy",
        "raw_prompt": "Diseña una estrategia de particionamiento horizontal (sharding) por hash de tenant_id para una tabla de 500 millones de registros en PostgreSQL.",
        "compressed_payload": "[H::DB] SHARD strategy=hash key=tenant_id rows=500M engine=PostgreSQL"
    },
    # --- DOMINIO 6: SISTEMAS ASÍNCRONOS ([H::ASYNC]) ---
    {
        "id": "HEKT-CORE-011", "domain": "async_systems", "symbolic_namespace": "[H::ASYNC]", "complexity": 3, "language_parity": ["es"], "task_type": "pipeline_design",
        "raw_prompt": "Pipeline de pagos con reintentos exponenciales, dead-letter queue tras 5 fallos y orden por usuario.",
        "compressed_payload": "[H::ASYNC] PIPELINE payment_events retry=exp_backoff max=5 dlq=true ordering=by_user"
    },
    {
        "id": "HEKT-CORE-012", "domain": "async_systems", "symbolic_namespace": "[H::ASYNC]", "complexity": 3, "language_parity": ["en"], "task_type": "rate_limiter",
        "raw_prompt": "Implement a distributed rate limiter using Redis token bucket algorithm allowing 100 requests per minute per API key.",
        "compressed_payload": "[H::ASYNC] RATE_LIMIT alg=token_bucket store=Redis limit=100/min key=api_key"
    },
    # --- DOMINIO 7: DISEÑO DE APIS ([H::API]) ---
    {
        "id": "HEKT-CORE-013", "domain": "api_design", "symbolic_namespace": "[H::API]", "complexity": 1, "language_parity": ["en"], "task_type": "endpoint_design",
        "raw_prompt": "Design an idempotent REST endpoint to revoke all active sessions except the current one.",
        "compressed_payload": "[H::API] ENDPOINT DELETE /users/me/sessions?except=current idempotent=true"
    },
    {
        "id": "HEKT-CORE-014", "domain": "api_design", "symbolic_namespace": "[H::API]", "complexity": 2, "language_parity": ["es"], "task_type": "graphql_schema",
        "raw_prompt": "Define un esquema GraphQL con paginación basada en cursor para consultar transacciones de usuario.",
        "compressed_payload": "[H::API] GRAPHQL type=Transaction query=userTransactions pagination=cursor"
    },
    # --- DOMINIO 8: REDES E INFRAESTRUCTURA ([H::NET]) ---
    {
        "id": "HEKT-CORE-015", "domain": "network_infrastructure", "symbolic_namespace": "[H::NET]", "complexity": 2, "language_parity": ["es"], "task_type": "firewall_rule",
        "raw_prompt": "Bloquea tráfico entrante a 10.0.4.0/24 excepto HTTPS (443) desde la VPN corporativa.",
        "compressed_payload": "[H::NET] RULE action=DROP target=10.0.4.0/24 allow=[src=VPN dport=443 proto=tcp]"
    },
    {
        "id": "HEKT-CORE-016", "domain": "network_infrastructure", "symbolic_namespace": "[H::NET]", "complexity": 3, "language_parity": ["en"], "task_type": "dns_sec",
        "raw_prompt": "Configure DNSSEC signing on BIND9 authoritative nameserver with automatic key rollovers.",
        "compressed_payload": "[H::NET] DNSSEC nameserver=BIND9 action=enable rollover=automatic"
    },
    # --- DOMINIO 9: CLOUD / IAC ([H::CLOUD]) ---
    {
        "id": "HEKT-CORE-017", "domain": "cloud_infrastructure", "symbolic_namespace": "[H::CLOUD]", "complexity": 3, "language_parity": ["en"], "task_type": "iac_provisioning",
        "raw_prompt": "Provision AWS S3 bucket with KMS encryption, block public access, and Glacier lifecycle after 90 days.",
        "compressed_payload": "[H::CLOUD] AWS_S3 encryption=KMS public_access=block lifecycle=Glacier_90d"
    },
    {
        "id": "HEKT-CORE-018", "domain": "cloud_infrastructure", "symbolic_namespace": "[H::CLOUD]", "complexity": 2, "language_parity": ["es"], "task_type": "azure_aks",
        "raw_prompt": "Despliega un clúster de Azure Kubernetes Service (AKS) con nodos Spot para optimizar costes.",
        "compressed_payload": "[H::CLOUD] AZURE_AKS cluster=production node_pool=Spot optimize=cost"
    },
    # --- DOMINIO 10: DEVOPS ([H::DEVOPS]) ---
    {
        "id": "HEKT-CORE-019", "domain": "devops", "symbolic_namespace": "[H::DEVOPS]", "complexity": 2, "language_parity": ["es"], "task_type": "pipeline_optimization",
        "raw_prompt": "Optimiza GitHub Actions usando caché de Docker Layer y Maven para bajar de 18 a 5 min.",
        "compressed_payload": "[H::DEVOPS] GITHUB_ACTIONS target_time<5m strategy=[docker_cache, maven_cache]"
    },
    {
        "id": "HEKT-CORE-020", "domain": "devops", "symbolic_namespace": "[H::DEVOPS]", "complexity": 3, "language_parity": ["en"], "task_type": "gitops_argo",
        "raw_prompt": "Configure ArgoCD application synchronization policy with automated self-healing and pruning enabled.",
        "compressed_payload": "[H::DEVOPS] ARGOCD sync_policy=[self_heal, prune] state=active"
    },
    # --- DOMINIO 11: SISTEMAS DISTRIBUIDOS ([H::DIST]) ---
    {
        "id": "HEKT-CORE-021", "domain": "distributed_systems", "symbolic_namespace": "[H::DIST]", "complexity": 3, "language_parity": ["en"], "task_type": "consensus_analysis",
        "raw_prompt": "Evaluate Raft vs Paxos for a distributed metadata store requiring linearizable reads across 5 nodes.",
        "compressed_payload": "[H::DIST] CONSENSUS nodes=5 requirements=[leader, linearizable_reads] evaluate=[Raft, Paxos]"
    },
    {
        "id": "HEKT-CORE-022", "domain": "distributed_systems", "symbolic_namespace": "[H::DIST]", "complexity": 3, "language_parity": ["es"], "task_type": "vector_clock",
        "raw_prompt": "Implementa relojes vectoriales (Vector Clocks) para detección de conflictos en almacenamiento multimaster.",
        "compressed_payload": "[H::DIST] VECTOR_CLOCK model=multimaster conflict_resolution=causal"
    },
    # --- DOMINIO 12: KUBERNETES ([H::K8S]) ---
    {
        "id": "HEKT-CORE-023", "domain": "container_orchestration", "symbolic_namespace": "[H::K8S]", "complexity": 2, "language_parity": ["es"], "task_type": "k8s_deployment",
        "raw_prompt": "Configura HorizontalPodAutoscaler para payment-service basado en 70% CPU, min 3, max 15 pods.",
        "compressed_payload": "[H::K8S] HPA deployment=payment-service target_cpu=70% replicas=[3, 15]"
    },
    {
        "id": "HEKT-CORE-024", "domain": "container_orchestration", "symbolic_namespace": "[H::K8S]", "complexity": 3, "language_parity": ["en"], "task_type": "network_policy",
        "raw_prompt": "Apply Kubernetes NetworkPolicy isolating namespace 'secure-zone' to accept ingress only from frontend pods.",
        "compressed_payload": "[H::K8S] NETWORK_POLICY namespace=secure-zone ingress_from=frontend_pods"
    },
    # --- DOMINIO 13: AUDITORÍA DE SEGURIDAD ([H::SEC_AUDIT]) ---
    {
        "id": "HEKT-CORE-025", "domain": "sec_audit", "symbolic_namespace": "[H::SEC_AUDIT]", "complexity": 3, "language_parity": ["en"], "task_type": "crypto_review",
        "raw_prompt": "Audit JWT auth protocol using HS256 with 24h expiration. Suggest hardening measures.",
        "compressed_payload": "[H::SEC_AUDIT] AUDIT jwt current=[HS256, 24h] recommend=[RS256, 15m]"
    },
    {
        "id": "HEKT-CORE-026", "domain": "sec_audit", "symbolic_namespace": "[H::SEC_AUDIT]", "complexity": 3, "language_parity": ["es"], "task_type": "owasp_top10",
        "raw_prompt": "Mitiga vulnerabilidades de Inyección SQL y Broken Object Level Authorization (BOLA) en API REST.",
        "compressed_payload": "[H::SEC_AUDIT] OWASP fix=[SQLi, BOLA] scope=REST_API"
    },
    # --- DOMINIO 14: INGENIERÍA DE DATOS ([H::DATA_ENG]) ---
    {
        "id": "HEKT-CORE-027", "domain": "data_engineering", "symbolic_namespace": "[H::DATA_ENG]", "complexity": 3, "language_parity": ["es"], "task_type": "stream_processing",
        "raw_prompt": "Job en Apache Flink procesando telemetría IoT desde Kafka con ventana deslizante de 5 min.",
        "compressed_payload": "[H::DATA_ENG] FLINK src=Kafka sink=ClickHouse window=sliding_5m"
    },
    {
        "id": "HEKT-CORE-028", "domain": "data_engineering", "symbolic_namespace": "[H::DATA_ENG]", "complexity": 3, "language_parity": ["en"], "task_type": "spark_optimization",
        "raw_prompt": "Optimize Spark SQL join performance on large datasets using broadcast hash join and proper partitioning.",
        "compressed_payload": "[H::DATA_ENG] SPARK_SQL optimization=broadcast_hash_join partitioning=optimal"
    },
    # --- DOMINIO 15: COMPILADORES ([H::COMPILER]) ---
    {
        "id": "HEKT-CORE-029", "domain": "compiler", "symbolic_namespace": "[H::COMPILER]", "complexity": 3, "language_parity": ["en"], "task_type": "opt_pass",
        "raw_prompt": "Optimize LLVM IR pass for loop unrolling and dead code elimination for AVX-512 target.",
        "compressed_payload": "[H::COMPILER] LLVM_PASS target=AVX-512 passes=[loop_unroll, DCE] opt=O3"
    },
    {
        "id": "HEKT-CORE-030", "domain": "compiler", "symbolic_namespace": "[H::COMPILER]", "complexity": 3, "language_parity": ["es"], "task_type": "wasm_compilation",
        "raw_prompt": "Compila módulo de criptografía en C++ a WebAssembly (Wasm) optimizado para tamaño binario mínimo.",
        "compressed_payload": "[H::COMPILER] WASM source=C++ optimize=min_size"
    },
    # --- DOMINIO 16: SISTEMAS EMBEBIDOS ([H::EMBEDDED]) ---
    {
        "id": "HEKT-CORE-031", "domain": "embedded", "symbolic_namespace": "[H::EMBEDDED]", "complexity": 2, "language_parity": ["es"], "task_type": "rtos_task",
        "raw_prompt": "Configura tarea FreeRTOS de alta prioridad para muestreo SPI a 1 kHz con cola segura ISR.",
        "compressed_payload": "[H::EMBEDDED] FREERTOS task=high_pri trigger=SPI_1kHz queue=isr_safe"
    },
    {
        "id": "HEKT-CORE-032", "domain": "embedded", "symbolic_namespace": "[H::EMBEDDED]", "complexity": 3, "language_parity": ["en"], "task_type": "watchdog_timer",
        "raw_prompt": "Configure hardware watchdog timer with 500ms timeout and safe state recovery routine on microcontroller.",
        "compressed_payload": "[H::EMBEDDED] WATCHDOG timeout=500ms recovery=safe_state"
    },
    # --- DOMINIO 17: OBSERVABILIDAD ([H::OBSERV]) ---
    {
        "id": "HEKT-CORE-033", "domain": "observability", "symbolic_namespace": "[H::OBSERV]", "complexity": 2, "language_parity": ["en"], "task_type": "tracing_spec",
        "raw_prompt": "Configure OpenTelemetry distributed tracing context propagation over gRPC with 10% sampling.",
        "compressed_payload": "[H::OBSERV] OPENTELEMETRY transport=gRPC sampling=10%"
    },
    {
        "id": "HEKT-CORE-034", "domain": "observability", "symbolic_namespace": "[H::OBSERV]", "complexity": 2, "language_parity": ["es"], "task_type": "prometheus_alert",
        "raw_prompt": "Define alerta en Prometheus cuando la tasa de errores HTTP 5xx supere el 2% durante 5 minutos.",
        "compressed_payload": "[H::OBSERV] PROMETHEUS alert=HTTP_5xx threshold=2% window=5m"
    },
    # --- DOMINIO 18: ALMACENAMIENTO ([H::STORAGE]) ---
    {
        "id": "HEKT-CORE-035", "domain": "storage", "symbolic_namespace": "[H::STORAGE]", "complexity": 3, "language_parity": ["es"], "task_type": "cluster_config",
        "raw_prompt": "Modelar clúster Ceph con Erasure Coding 4+2 tolerando caída de hasta 2 nodos.",
        "compressed_payload": "[H::STORAGE] CEPH erasure_coding=4+2 tolerance=2_nodes"
    },
    {
        "id": "HEKT-CORE-036", "domain": "storage", "symbolic_namespace": "[H::STORAGE]", "complexity": 3, "language_parity": ["en"], "task_type": "zfs_pool",
        "raw_prompt": "Configure ZFS RAID-Z2 storage pool with L2ARC SSD caching and compression enabled.",
        "compressed_payload": "[H::STORAGE] ZFS pool=RAID-Z2 cache=L2ARC compression=on"
    },
    # --- DOMINIO 19: FINANZAS CUANTITATIVAS ([H::QUANT]) ---
    {
        "id": "HEKT-CORE-037", "domain": "quantitative_finance", "symbolic_namespace": "[H::QUANT]", "complexity": 3, "language_parity": ["en"], "task_type": "risk_engine",
        "raw_prompt": "Calculate Monte Carlo Value at Risk (VaR) at 99% confidence over 10-day horizon with GARCH volatility.",
        "compressed_payload": "[H::QUANT] VAR method=Monte_Carlo conf=0.99 horizon=10d vol=GARCH"
    },
    {
        "id": "HEKT-CORE-038", "domain": "quantitative_finance", "symbolic_namespace": "[H::QUANT]", "complexity": 3, "language_parity": ["es"], "task_type": "order_book",
        "raw_prompt": "Implementa motor de emparejamiento de libro de órdenes (Order Book matching engine) con prioridad precio-tiempo en memoria.",
        "compressed_payload": "[H::QUANT] MATCHING_ENGINE logic=price_time_priority memory=in_memory"
    },
    # --- DOMINIO 20: IA / AGENTES AVANZADOS ([H::AGENTS]) ---
    {
        "id": "HEKT-CORE-039", "domain": "autonomous_agents", "symbolic_namespace": "[H::AGENTS]", "complexity": 3, "language_parity": ["es"], "task_type": "agent_loop",
        "raw_prompt": "Define el ciclo de razonamiento y ejecución ReAct para un agente autónomo con bucle de autocorrección de errores de código.",
        "compressed_payload": "[H::AGENTS] REACT_LOOP workflow=[reason, act, observe] self_correct=enabled"
    },
    {
        "id": "HEKT-CORE-040", "domain": "autonomous_agents", "symbolic_namespace": "[H::AGENTS]", "complexity": 3, "language_parity": ["en"], "task_type": "multi_agent_consensus",
        "raw_prompt": "Establish multi-agent voting protocol for code review verification among specialized security and architecture agents.",
        "compressed_payload": "[H::AGENTS] MULTI_AGENT protocol=voting roles=[security, architecture]"
    }
]

def main():
    print(f"Generando dataset purificado v2.3 con {len(CASOS_NUCLEO)} núcleos técnicos únicos...")
    os.makedirs("data", exist_ok=True)
    ruta_salida = "data/arca_symbolic_benchmark_extended.jsonl"
    
    with open(ruta_salida, "w", encoding="utf-8") as f:
        for c in CASOS_NUCLEO:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"[OK] Dataset núcleo v2.3 ampliado a 40 casos guardado en: {ruta_salida}")

if __name__ == "__main__":
    main()
