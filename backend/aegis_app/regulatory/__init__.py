"""
Regulatory content ingestion & validation subsystem.

Pipeline (spec section 90):
    AUTHORITATIVE SOURCE -> LICENCE CHECK -> DOWNLOAD -> ARCHIVE -> HASH ->
    PARSE -> STRUCTURE -> NORMALIZE -> VALIDATE -> REVIEW -> PUBLISH ->
    MAP CONTROLS -> APPLICABILITY -> EVIDENCE -> ASSESS -> REPORT ->
    MONITOR SOURCE -> CHANGE DETECTION -> IMPACT ANALYSIS

Nothing in this subsystem invents regulatory text. If a source cannot be
retrieved and no committed fixture exists, the framework is recorded as
SOURCE_RETRIEVAL_BLOCKED and left unpublished.
"""

PARSER_VERSION = "0.2.0"
SCHEMA_VERSION = "1.0.0"
VALIDATION_VERSION = "1.0.0"
