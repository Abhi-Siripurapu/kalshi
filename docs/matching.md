# Duplicate Market Matching Policy

This document defines the exact rules for identifying duplicate markets across venues. The goal is zero false positives - every matched pair must be truly identical in resolution.

## Two-Stage Process

### Stage 1: Candidate Generation (Loose)
Generate potential matches using similarity heuristics. High recall, accept false positives.

### Stage 2: Spec Check (Strict)
Apply hard rules to eliminate false positives. Zero tolerance for ambiguity.

## Stage 1: Candidate Generation

### Title Normalization
```python
def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)  # Remove punctuation
    title = re.sub(r'\s+', ' ', title)      # Normalize whitespace
    title = title.strip()
    return title
```

### Synonym Mapping
```python
SYNONYMS = {
    "xai": ["grok", "x.ai"],
    "google": ["alphabet", "googl"],
    "openai": ["chatgpt", "gpt"],
    "anthropic": ["claude"],
    "meta": ["facebook", "fb"],
    "tesla": ["tsla"],
    "nvidia": ["nvda"],
    "microsoft": ["msft"],
    "amazon": ["amzn", "aws"]
}
```

### Similarity Scoring
1. **Exact Title Match**: Score = 1.0
2. **Normalized Title Match**: Score = 0.9
3. **Synonym-Adjusted Match**: Score = 0.8
4. **Cosine Similarity > 0.75**: Score = cosine_score
5. **Tag Overlap**: Score based on shared mapping_tags

### Candidate Criteria
Generate candidate pair if ANY of:
- Similarity score ≥ 0.75
- ≥3 shared mapping_tags with high confidence
- Manual "force_pair" override

## Stage 2: Spec Check (Hard Rules)

### Resolution Requirements
```python
def spec_check(market_a: Market, market_b: Market) -> SpecResult:
    checks = [
        resolution_source_check(market_a, market_b),
        resolution_timing_check(market_a, market_b),
        outcome_semantics_check(market_a, market_b),
        measurement_criteria_check(market_a, market_b),
        jurisdiction_check(market_a, market_b)
    ]
    
    return SpecResult(
        spec_ok=all(check.passed for check in checks),
        checks=checks,
        confidence=calculate_confidence(checks)
    )
```

### 1. Resolution Source Check
**Rule**: Markets must resolve using identical data sources.

**Implementation**:
```python
RESOLUTION_SOURCES = {
    "cpi": ["https://www.bls.gov/cpi/", "bls.gov", "bureau of labor statistics"],
    "fed_funds": ["federalreserve.gov", "fomc", "federal reserve"],
    "earnings": ["earnings call", "quarterly earnings", "sec filing"],
    "election": ["ap.org", "associated press", "official election results"],
    "weather": ["noaa.gov", "national weather service"],
    "sports": ["espn.com", "official league", "nfl.com", "nba.com"]
}

def resolution_source_check(market_a: Market, market_b: Market) -> CheckResult:
    source_a = normalize_resolution_source(market_a.resolution_source)
    source_b = normalize_resolution_source(market_b.resolution_source)
    
    return CheckResult(
        passed=(source_a == source_b),
        details=f"Sources: {source_a} vs {source_b}"
    )
```

### 2. Resolution Timing Check
**Rule**: Markets must resolve at the same time with same timezone handling.

```python
def resolution_timing_check(market_a: Market, market_b: Market) -> CheckResult:
    # Allow up to 1 hour difference for timezone ambiguity
    time_diff = abs(market_a.resolution_ts - market_b.resolution_ts)
    max_allowed_diff = 3600  # 1 hour in seconds
    
    return CheckResult(
        passed=(time_diff <= max_allowed_diff),
        details=f"Time difference: {time_diff}s (max: {max_allowed_diff}s)"
    )
```

### 3. Outcome Semantics Check
**Rule**: Outcomes must have identical meaning and measurement.

```python
def outcome_semantics_check(market_a: Market, market_b: Market) -> CheckResult:
    # Check outcome types match
    if len(market_a.outcomes) != len(market_b.outcomes):
        return CheckResult(False, "Different number of outcomes")
    
    # For binary markets
    if all(o.type == "binary" for o in market_a.outcomes):
        return CheckResult(True, "Binary outcomes identical")
    
    # For categorical markets, check mapping_tags
    tags_a = [o.mapping_tags for o in market_a.outcomes]
    tags_b = [o.mapping_tags for o in market_b.outcomes]
    
    return CheckResult(
        passed=tags_match(tags_a, tags_b),
        details=f"Tag comparison: {tags_a} vs {tags_b}"
    )
```

### 4. Measurement Criteria Check
**Rule**: Markets must measure the same metric with identical criteria.

```python
MEASUREMENT_PATTERNS = {
    "cpi_mom": r"cpi.*month.*over.*month",
    "cpi_yoy": r"cpi.*year.*over.*year", 
    "fed_rate": r"federal.*funds.*rate",
    "stock_price": r"(stock|share).*price.*(above|below|over|under)",
    "revenue": r"revenue.*(q1|q2|q3|q4|quarter)",
    "earnings": r"(earnings|eps).*per.*share"
}

def measurement_criteria_check(market_a: Market, market_b: Market) -> CheckResult:
    desc_a = normalize_description(market_a.description)
    desc_b = normalize_description(market_b.description)
    
    # Check for contradictory patterns
    for pattern_name, pattern in MEASUREMENT_PATTERNS.items():
        match_a = bool(re.search(pattern, desc_a, re.IGNORECASE))
        match_b = bool(re.search(pattern, desc_b, re.IGNORECASE))
        
        if match_a != match_b:
            return CheckResult(False, f"Measurement mismatch: {pattern_name}")
    
    return CheckResult(True, "Measurement criteria compatible")
```

### 5. Jurisdiction Check
**Rule**: Markets must apply to the same jurisdiction/scope.

```python
JURISDICTION_KEYWORDS = {
    "us": ["united states", "usa", "us ", "american"],
    "global": ["worldwide", "global", "international"],
    "eu": ["european union", "europe", "eu "],
    "company": ["[company_name]", "inc", "corp", "ltd"]
}

def jurisdiction_check(market_a: Market, market_b: Market) -> CheckResult:
    # Extract jurisdiction from titles and descriptions
    jurisdiction_a = extract_jurisdiction(market_a)
    jurisdiction_b = extract_jurisdiction(market_b)
    
    return CheckResult(
        passed=(jurisdiction_a == jurisdiction_b),
        details=f"Jurisdictions: {jurisdiction_a} vs {jurisdiction_b}"
    )
```

## Manual Overrides

### Force Pair
```json
{
    "force_pairs": [
        {
            "kalshi_market_id": "INXD-25JAN31",
            "polymarket_market_id": "0x1234...",
            "reason": "Identical resolution despite title differences",
            "added_by": "trader_id",
            "added_ts": 1704067200
        }
    ]
}
```

### Blacklist
```json
{
    "blacklist_pairs": [
        {
            "kalshi_market_id": "CPI-25JAN15", 
            "polymarket_market_id": "0x5678...",
            "reason": "Different measurement periods (MoM vs YoY)",
            "added_by": "trader_id",
            "added_ts": 1704067200
        }
    ]
}
```

## Output Format

```python
@dataclass
class DuplicatePair:
    kalshi_market_id: str
    polymarket_market_id: str
    similarity_score: float      # 0.0 to 1.0
    spec_ok: bool               # Passed all spec checks
    confidence: float           # Overall confidence (0.0 to 1.0)
    checks: list[CheckResult]   # Individual check results
    notes: str                  # Human-readable explanation
    override_type: str          # None | "force" | "blacklist"
    last_updated_ts: int        # When this pairing was last validated
```

## Confidence Scoring

```python
def calculate_confidence(checks: list[CheckResult]) -> float:
    if not all(check.passed for check in checks):
        return 0.0
    
    # Base confidence from spec checks
    base_confidence = 0.8
    
    # Boost for exact title match
    if similarity_score >= 0.95:
        base_confidence += 0.15
    
    # Boost for identical resolution source
    if resolution_sources_identical():
        base_confidence += 0.05
    
    return min(1.0, base_confidence)
```

## Validation Pipeline

```python
async def find_duplicate_pairs() -> list[DuplicatePair]:
    # 1. Load markets from both venues
    kalshi_markets = await load_kalshi_markets()
    polymarket_markets = await load_polymarket_markets()
    
    # 2. Generate candidates
    candidates = []
    for k_market in kalshi_markets:
        for p_market in polymarket_markets:
            score = calculate_similarity(k_market, p_market)
            if score >= 0.75:
                candidates.append((k_market, p_market, score))
    
    # 3. Apply spec checks
    pairs = []
    for k_market, p_market, score in candidates:
        spec_result = spec_check(k_market, p_market)
        
        pair = DuplicatePair(
            kalshi_market_id=k_market.market_id,
            polymarket_market_id=p_market.market_id,
            similarity_score=score,
            spec_ok=spec_result.spec_ok,
            confidence=spec_result.confidence,
            checks=spec_result.checks,
            notes=generate_notes(spec_result),
            override_type=check_overrides(k_market, p_market),
            last_updated_ts=int(time.time())
        )
        
        pairs.append(pair)
    
    return pairs
```

## Error Handling

1. **Missing Resolution Source**: Pair gets spec_ok=False
2. **Ambiguous Timeline**: Manual review required
3. **Contradictory Descriptions**: Automatic blacklist
4. **API Errors**: Retry with exponential backoff
5. **Schema Changes**: Alert and graceful degradation

## Monitoring

- **False Positive Rate**: Track pairs that failed in reality
- **False Negative Rate**: Track missed arbitrage opportunities  
- **Spec Check Performance**: Ensure < 100ms per pair
- **Override Usage**: Monitor manual intervention frequency
- **Market Coverage**: Ensure all major events are matched