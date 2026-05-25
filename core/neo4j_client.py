"""
Neo4j KG Client — all graph operations.
Connects to Neo4j Desktop at neo4j://127.0.0.1:7687

LLM: Parley API (OpenAI-compatible)
  Base URL : https://keys.theparley.org/v1
  Models   : gpt-4o, gpt-4o-mini, o3, gpt-5.1
"""
import uuid, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from extraction_engine import auto_generate_negation


class Neo4jKGClient:

    def __init__(self, uri="neo4j://127.0.0.1:7687",
                 user="neo4j", password="password123", database="neo4j"):
        from neo4j import GraphDatabase
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._db = database
        with self._driver.session(database=self._db) as s:
            s.run("RETURN 1")
        print(f"[ok] Neo4j connected: {uri}  db={database}")

    def _session(self):
        return self._driver.session(database=self._db)

    # -- MERGE CONCEPT ------------------------------------------------------
    def merge_concept(self, label: str, source_file: str,
                      location: str = "", source_type: str = "rule",
                      course_id: str = None, module_name: str = None) -> bool:
        label = label.lower().strip()
        if not label or len(label) < 2:
            return False
        with self._session() as s:
            # Use EXISTS check — reliable way to detect new vs existing node
            result = s.run("""
                OPTIONAL MATCH (existing:Concept {label: $label})
                WITH existing IS NULL AS is_new
                MERGE (c:Concept {label: $label})
                ON CREATE SET c.node_id         = $nid,
                              c.source_file     = $sf,
                              c.source_location = $loc,
                              c.source_type     = $st,
                              c.course_id       = $cid,
                              c.module_name     = $mod,
                              c.created_at      = $ts
                ON MATCH SET  c.course_id       = COALESCE(c.course_id, $cid),
                              c.module_name     = COALESCE(c.module_name, $mod)
                RETURN is_new
            """, label=label, nid=str(uuid.uuid4()), sf=source_file,
                 loc=location, st=source_type,
                 cid=course_id, mod=module_name,
                 ts=datetime.now().isoformat())
            row = result.single()
            return bool(row and row["is_new"])

    # -- MERGE RELATIONSHIP -------------------------------------------------
    def merge_relationship(self, src: str, rel_type: str, tgt: str,
                           source_file: str) -> bool:
        src = src.lower().strip()
        tgt = tgt.lower().strip()
        if not src or not tgt or src == tgt:
            return False
        # Whitelist valid relationship types to prevent Cypher injection
        valid_types = {"IS_A", "HAS_PROPERTY", "REQUIRES", "CONSISTS_OF",
                       "EXAMPLE_OF", "LEADS_TO", "CONTRASTS_WITH", "DESCRIBES"}
        if rel_type not in valid_types:
            return False
        with self._session() as s:
            s.run(f"""
                MERGE (a:Concept {{label: $src}})
                MERGE (b:Concept {{label: $tgt}})
                MERGE (a)-[:{rel_type} {{source_file: $sf}}]->(b)
            """, src=src, tgt=tgt, sf=source_file)
        return True

    # -- CREATE FACT --------------------------------------------------------
    def create_fact(self, concept_label: str, claim: str, source_file: str,
                    location: str = "", priority: str = "MEDIUM",
                    is_negation: bool = False) -> bool:
        concept_label = concept_label.lower().strip()
        claim = claim.strip()
        if not claim or len(claim) < 20:
            return False
        negation = claim if is_negation else auto_generate_negation(claim)
        with self._session() as s:
            s.run("""
                MERGE (c:Concept {label: $label})
                CREATE (f:Fact {
                    fact_id:         $fid,
                    claim:           $claim,
                    negation:        $negation,
                    priority:        $priority,
                    is_negation:     $is_neg,
                    source_file:     $sf,
                    source_location: $loc,
                    created_at:      $ts
                })
                CREATE (f)-[:DESCRIBES]->(c)
                CREATE (c)-[:HAS_PROPERTY]->(f)
            """, label=concept_label, fid=str(uuid.uuid4()),
                 claim=claim, negation=negation, priority=priority,
                 is_neg=is_negation, sf=source_file,
                 loc=location, ts=datetime.now().isoformat())
        return True

    # -- CREATE EXAMPLE -----------------------------------------------------
    def create_example(self, concept_label: str, content: str,
                       source_file: str, location: str = "") -> bool:
        concept_label = concept_label.lower().strip()
        with self._session() as s:
            s.run("""
                MERGE (c:Concept {label: $label})
                CREATE (e:Example {
                    example_id:      $eid,
                    content:         $content,
                    source_file:     $sf,
                    source_location: $loc,
                    created_at:      $ts
                })
                CREATE (e)-[:EXAMPLE_OF]->(c)
            """, label=concept_label, eid=str(uuid.uuid4()),
                 content=content, sf=source_file,
                 loc=location, ts=datetime.now().isoformat())
        return True

    # -- DOMAIN CONFIG ------------------------------------------------------
    def write_domain_config(self, config: dict):
        """Write domain config for a course. Uses domain_name + course_id as composite key.
        FIX (BUG 15): also stores modules list so app never needs COURSE_REGISTRY at runtime.
        """
        course_id = config.get("domain_name", "")
        with self._session() as s:
            s.run("""
                MERGE (d:DomainConfig {domain_name: $name, course_id: $cid})
                SET d.domain_id            = $did,
                    d.in_domain_keywords   = $in_kw,
                    d.boundary_terms       = $bnd,
                    d.excluded_terms       = $excl,
                    d.prerequisite_courses = $prereqs,
                    d.course_name          = $cname,
                    d.modules              = $modules,
                    d.updated_at           = $ts
            """, name=config["domain_name"], cid=course_id, did=str(uuid.uuid4()),
                 in_kw=config["in_domain_keywords"],
                 bnd=config["boundary_terms"],
                 excl=config["excluded_terms"],
                 prereqs=config.get("prerequisite_courses", []),
                 cname=config.get("course_name", ""),
                 modules=config.get("modules", []),
                 ts=datetime.now().isoformat())

    def get_all_concepts(self, limit: int = 50) -> list:
        """Return all concept labels from the KG for topic selection."""
        try:
            with self._session() as s:
                result = s.run(
                    "MATCH (c:Concept) RETURN c.label AS label "
                    "ORDER BY c.label LIMIT $limit",
                    limit=limit
                )
                return [r["label"] for r in result if r["label"]]
        except Exception:
            return []

    def get_domain_config(self, course_id: str = None) -> dict:
        """Fetch domain config for a specific course. Falls back to any config if course_id not specified."""
        with self._session() as s:
            if course_id:
                r = s.run(
                    "MATCH (d:DomainConfig {course_id: $cid}) RETURN d LIMIT 1",
                    cid=course_id
                ).single()
            else:
                # Fallback: get any domain config
                r = s.run("MATCH (d:DomainConfig) RETURN d LIMIT 1").single()
            if r:
                d = dict(r["d"])
                return {
                    "domain_name":          d.get("domain_name", ""),
                    "course_name":          d.get("course_name", ""),
                    "in_domain_keywords":   list(d.get("in_domain_keywords", [])),
                    "boundary_terms":       list(d.get("boundary_terms", [])),
                    "excluded_terms":       list(d.get("excluded_terms", [])),
                    "prerequisite_courses": list(d.get("prerequisite_courses", [])),
                    "modules":              list(d.get("modules", [])),
                }
        return {}

    # -- READ OPERATIONS ----------------------------------------------------
    def get_all_facts(self) -> list:
        with self._session() as s:
            r = s.run("""
                MATCH (f:Fact)-[:DESCRIBES]->(c:Concept)
                RETURN f.fact_id         AS fact_id,
                       f.claim           AS claim,
                       f.negation        AS negation,
                       c.label           AS concept,
                       f.priority        AS priority,
                       f.source_file     AS source_file,
                       f.source_location AS source_location
                ORDER BY f.priority DESC
            """)
            return [dict(row) for row in r]

    def get_facts_for_concept(self, concept_label: str) -> list:
        with self._session() as s:
            r = s.run("""
                MATCH (c:Concept {label: $label})
                OPTIONAL MATCH (f1:Fact)-[:DESCRIBES]->(c)
                OPTIONAL MATCH (c)-[:HAS_PROPERTY]->(f2:Fact)
                WITH c, collect(f1) + collect(f2) AS facts
                UNWIND facts AS f
                WITH DISTINCT f
                WHERE f IS NOT NULL
                RETURN f.fact_id         AS fact_id,
                       f.claim           AS claim,
                       f.negation        AS negation,
                       f.priority        AS priority,
                       f.source_file     AS source_file,
                       f.source_location AS source_location
                ORDER BY f.priority DESC
            """, label=concept_label.lower().strip())
            return [dict(row) for row in r]

    def get_stats(self) -> dict:
        with self._session() as s:
            concepts = s.run("MATCH (c:Concept) RETURN count(c) AS n").single()["n"]
            facts    = s.run("MATCH (f:Fact)    RETURN count(f) AS n").single()["n"]
            rels     = s.run("MATCH ()-[r]->()  RETURN count(r) AS n").single()["n"]
            files    = s.run(
                "MATCH (c:Concept) RETURN count(DISTINCT c.source_file) AS n"
            ).single()["n"]
        return {"concepts": concepts, "facts": facts,
                "relationships": rels, "source_files": files}

    def get_ingested_files(self) -> list:
        with self._session() as s:
            # Fixed: aggregate facts separately to avoid OPTIONAL MATCH count issues
            r = s.run("""
                MATCH (c:Concept)
                WITH c.source_file AS fn, count(c) AS concepts
                RETURN fn AS filename, concepts
                ORDER BY fn
            """)
            file_rows = [dict(row) for row in r if row["filename"]]

            # Get fact counts per file separately
            r2 = s.run("""
                MATCH (f:Fact)
                RETURN f.source_file AS fn, count(f) AS facts
            """)
            fact_counts = {row["fn"]: row["facts"] for row in r2}

        return [
            {
                "filename": row["filename"],
                "concepts": row["concepts"],
                "facts":    fact_counts.get(row["filename"], 0),
                "format":   (row["filename"] or "").split(".")[-1].upper(),
            }
            for row in file_rows
        ]

    # -- LLM CLIENT (Parley — OpenAI-compatible) ----------------------------
    @staticmethod
    def get_llm_client(api_key: str, model: str = "gpt-4o"):
        """
        Returns a configured OpenAI client pointed at Parley's API.
        Usage:
            client, model = Neo4jKGClient.get_llm_client(api_key="YOUR_KEY")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.choices[0].message.content
        """
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://keys.theparley.org/v1"
        )
        return client, model

    @staticmethod
    def call_llm(prompt: str, api_key: str, model: str = "gpt-4o") -> str:
        """
        Simple one-shot LLM call via Parley.
        Returns the response text string.
        """
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://keys.theparley.org/v1"
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,   # low temp for factual educational responses
        )
        return response.choices[0].message.content.strip()

    # -- UTILITY ------------------------------------------------------------
    def clear_all(self):
        """⚠️ Wipe entire KG — use only for fresh re-ingestion."""
        with self._session() as s:
            s.run("MATCH (n) DETACH DELETE n")
        print("⚠️  KG cleared — all nodes and relationships deleted.")

    def close(self):
        self._driver.close()