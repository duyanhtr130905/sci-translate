GET_TRANSLATION = """
MATCH (source:Term {term: $term_name, language: $source_lang})
MATCH (source)-[:TRANSLATION_OF]-(target:Term)
WHERE target.language = $target_lang
RETURN source.term AS source_term, target.term AS target_term
LIMIT 1
"""

GET_TERMS_IN_TEXT = """
UNWIND $term_list AS term_name
MATCH (source:Term {term: term_name, language: $source_lang})
MATCH (source)-[:TRANSLATION_OF]-(target:Term)
WHERE target.language = $target_lang
RETURN source.term AS source_term, target.term AS target_term
"""

GET_TERM_FULL_INFO = """
MATCH (source:Term {term: $term_name, language: $source_lang})
MATCH (source)-[:TRANSLATION_OF]-(target:Term)
WHERE target.language = $target_lang
OPTIONAL MATCH (source)-[:SYNONYM_OF]-(syn:Term {language: $source_lang})
OPTIONAL MATCH (source)-[:IN_SUBDOMAIN]->(sd:Subdomain)
RETURN source.term AS term,
       target.term AS translation,
       collect(DISTINCT syn.term) AS synonyms,
       sd.name AS subdomain
LIMIT 1
"""