# Anti-Spam Patterns for UGC Platforms

> **Spike Research Document** - January 2026
> Pebble: `upt-863`

This document summarizes research into anti-spam best practices for user-generated content platforms, covering rate limiting, trust scoring, honeypots, OAuth signals, and industry standards.

---

## Table of Contents

1. [Progressive Rate Limiting Patterns](#1-progressive-rate-limiting-patterns)
2. [Trust Scoring Algorithms](#2-trust-scoring-algorithms)
3. [Honeypot Field Implementation](#3-honeypot-field-implementation)
4. [OAuth Trust Signals Integration](#4-oauth-trust-signals-integration)
5. [Industry Standards for UGC Spam Prevention](#5-industry-standards-for-ugc-spam-prevention)
6. [Recommended Implementation Strategy](#6-recommended-implementation-strategy)

---

## 1. Progressive Rate Limiting Patterns

### Algorithm Selection

| Algorithm | Best For | Trade-offs |
|-----------|----------|------------|
| **Token Bucket** | Burst-tolerant APIs | Allows temporary spikes; not perfectly smooth |
| **Sliding Window** | Production APIs requiring fairness | More complex; best balance of accuracy |
| **Fixed Window** | Simple implementations | Boundary spike issues |
| **Leaky Bucket** | Steady processing rate | No burst tolerance |

For UGC platforms, **sliding window** is recommended for public-facing APIs, with **token bucket** for internal services that need burst tolerance.

### Recommended Intervals by Operation Type

Based on industry practices, here are sensible defaults:

```
| Operation Type          | Rate Limit              | Rationale                        |
|-------------------------|-------------------------|----------------------------------|
| Read operations (GET)   | 100-200 req/min         | Low cost, high frequency         |
| Create content (POST)   | 10-30 req/min           | Resource intensive               |
| Update content (PUT)    | 20-50 req/min           | Moderate cost                    |
| Delete operations       | 5-10 req/min            | High risk, low legitimate need   |
| Authentication          | 5 req/min per IP        | Brute force prevention           |
| Search/query            | 30-60 req/min           | Can be expensive                 |
| File uploads            | 5-10 req/hour           | Very resource intensive          |
```

### Tiered Rate Limiting for Login/Auth

A proven pattern from Cloudflare's best practices:

1. **Tier 1**: 4 requests/minute → trigger CAPTCHA challenge
2. **Tier 2**: 10 requests/10 minutes → extended challenge
3. **Tier 3**: Exceed tier 2 → block for 24 hours

### Exponential Backoff Formula

For retry mechanisms after rate limit hits:

```typescript
const calculateBackoff = (attempt: number, baseMs = 100, maxMs = 32000): number => {
  const exponentialDelay = Math.pow(2, attempt) * baseMs;
  const jitter = Math.random() * baseMs; // Add jitter to prevent thundering herd
  return Math.min(exponentialDelay + jitter, maxMs);
};

// Results: 100ms, 200ms, 400ms, 800ms, 1600ms, 3200ms... (capped at maxMs)
```

### Response Headers

Always communicate limits to clients:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706054400
Retry-After: 60
```

### Implementation Example (Sliding Window with Redis)

```typescript
import Redis from 'ioredis';

interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetAt: number;
}

async function slidingWindowRateLimit(
  redis: Redis,
  key: string,
  limit: number,
  windowMs: number
): Promise<RateLimitResult> {
  const now = Date.now();
  const windowStart = now - windowMs;

  // Use Redis transaction for atomicity
  const multi = redis.multi();

  // Remove old entries outside the window
  multi.zremrangebyscore(key, 0, windowStart);

  // Count current requests in window
  multi.zcard(key);

  // Add current request
  multi.zadd(key, now, `${now}-${Math.random()}`);

  // Set expiry on the key
  multi.pexpire(key, windowMs);

  const results = await multi.exec();
  const currentCount = results?.[1]?.[1] as number ?? 0;

  return {
    allowed: currentCount < limit,
    remaining: Math.max(0, limit - currentCount - 1),
    resetAt: now + windowMs
  };
}
```

---

## 2. Trust Scoring Algorithms

### Core Principles

Trust scoring should evaluate users on multiple dimensions, treating new users with appropriate caution while rewarding established positive behavior.

### Trust Score Components

```typescript
interface TrustScore {
  // Base score (0-100)
  baseScore: number;

  // Component weights
  components: {
    accountAge: number;        // Weight: 0.15
    emailVerified: boolean;    // Weight: 0.10
    phoneVerified: boolean;    // Weight: 0.10
    oauthProvider: string;     // Weight: 0.15
    contentHistory: number;    // Weight: 0.20
    reportHistory: number;     // Weight: 0.15 (negative)
    engagementQuality: number; // Weight: 0.15
  };
}
```

### New User vs Established User Thresholds

```typescript
const USER_TIERS = {
  NEW: {
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    postLimit: 5,       // posts per day
    commentLimit: 20,   // comments per day
    requiresModeration: true,
    canUploadMedia: false
  },
  ESTABLISHING: {
    maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days
    postLimit: 20,
    commentLimit: 100,
    requiresModeration: 'sample', // 10% random sampling
    canUploadMedia: true
  },
  ESTABLISHED: {
    maxAge: Infinity,
    postLimit: 100,
    commentLimit: 500,
    requiresModeration: false,
    canUploadMedia: true
  }
};
```

### Trust Score Calculation

```typescript
function calculateTrustScore(user: User, history: UserHistory): number {
  let score = 0;

  // Account age (0-15 points)
  const ageInDays = (Date.now() - user.createdAt) / (1000 * 60 * 60 * 24);
  score += Math.min(15, ageInDays * 0.5);

  // Verification bonuses
  if (user.emailVerified) score += 10;
  if (user.phoneVerified) score += 10;

  // OAuth provider trust (0-15 points)
  const oauthTrust: Record<string, number> = {
    'google': 15,
    'apple': 15,
    'github': 12,
    'microsoft': 12,
    'facebook': 8,
    'twitter': 8,
    'discord': 5,
    'none': 0
  };
  score += oauthTrust[user.oauthProvider] ?? 0;

  // Content history (0-20 points)
  const approvedContent = history.postsApproved + history.commentsApproved;
  score += Math.min(20, approvedContent * 0.1);

  // Negative signals
  score -= history.reportsReceived * 5;
  score -= history.contentRemoved * 10;
  score -= history.suspensions * 20;

  // Engagement quality (0-15 points)
  if (history.totalEngagements > 0) {
    const positiveRatio = history.positiveEngagements / history.totalEngagements;
    score += positiveRatio * 15;
  }

  return Math.max(0, Math.min(100, score));
}
```

### Progressive Privilege Unlocking

```typescript
const TRUST_THRESHOLDS = {
  CAN_POST: 10,
  CAN_COMMENT: 5,
  CAN_UPLOAD_IMAGES: 25,
  CAN_UPLOAD_VIDEO: 40,
  CAN_POST_LINKS: 30,
  SKIP_MODERATION_QUEUE: 60,
  CAN_REPORT_OTHERS: 20,
  TRUSTED_REPORTER: 70,
  CAN_MODERATE: 85
};

function getUserCapabilities(trustScore: number): string[] {
  return Object.entries(TRUST_THRESHOLDS)
    .filter(([_, threshold]) => trustScore >= threshold)
    .map(([capability]) => capability);
}
```

---

## 3. Honeypot Field Implementation

### Overview

Honeypots trick bots into filling out invisible form fields that humans never see. Any submission with data in these fields is flagged as spam.

### Best Practices

1. **Realistic field names** - Use names like `email`, `phone`, `website` that bots expect
2. **Prevent autofill** - Use `autocomplete="one-time-code"` (more reliable than `autocomplete="off"`)
3. **Proper hiding** - Position off-screen, not `display: none` (bots may skip those)
4. **Accessibility** - Use `tabindex="-1"` and `aria-hidden="true"` for screen readers
5. **Time-based validation** - Track submission speed; bots submit in milliseconds

### Implementation

```tsx
// React component example
interface HoneypotFieldsProps {
  formLoadTime: number;
}

export function HoneypotFields({ formLoadTime }: HoneypotFieldsProps) {
  return (
    <>
      {/* Invisible honeypot field */}
      <div
        style={{
          position: 'absolute',
          left: '-9999px',
          top: '-9999px',
        }}
        aria-hidden="true"
      >
        <label htmlFor="website">Website</label>
        <input
          type="text"
          id="website"
          name="website"
          tabIndex={-1}
          autoComplete="one-time-code"
        />
      </div>

      {/* Timestamp field for timing validation */}
      <input
        type="hidden"
        name="_formLoadTime"
        value={formLoadTime}
      />
    </>
  );
}
```

### Server-Side Validation

```typescript
interface FormSubmission {
  website?: string;      // Honeypot field
  _formLoadTime?: number;
  // ... other fields
}

interface SpamCheckResult {
  isSpam: boolean;
  reason?: string;
  confidence: number;
}

function checkHoneypot(submission: FormSubmission): SpamCheckResult {
  // Check honeypot field
  if (submission.website && submission.website.trim().length > 0) {
    return {
      isSpam: true,
      reason: 'honeypot_filled',
      confidence: 0.95
    };
  }

  // Check submission timing
  const submissionTime = Date.now();
  const loadTime = submission._formLoadTime ?? submissionTime;
  const elapsedMs = submissionTime - loadTime;

  // Minimum 2 seconds for a human to fill a form
  const MIN_HUMAN_TIME_MS = 2000;

  if (elapsedMs < MIN_HUMAN_TIME_MS) {
    return {
      isSpam: true,
      reason: 'submission_too_fast',
      confidence: 0.85
    };
  }

  // Very long time might also be suspicious (bot retrying)
  const MAX_REASONABLE_TIME_MS = 30 * 60 * 1000; // 30 minutes

  if (elapsedMs > MAX_REASONABLE_TIME_MS) {
    return {
      isSpam: false, // Not spam, but flag for review
      reason: 'submission_delayed',
      confidence: 0.3
    };
  }

  return {
    isSpam: false,
    confidence: 0
  };
}
```

### CSS-Only Honeypot (Alternative)

```css
/* Hide with CSS positioning - harder for bots to detect */
.hp-field {
  position: absolute;
  left: -9999px;
  top: -9999px;
  width: 1px;
  height: 1px;
  overflow: hidden;
}

/* Alternative: visually hidden but accessible trap */
.hp-trap {
  opacity: 0;
  position: absolute;
  top: 0;
  left: 0;
  height: 0;
  width: 0;
  z-index: -1;
}
```

### Combining with Other Techniques

Honeypots work best as part of a layered defense:

```typescript
async function validateSubmission(
  submission: FormSubmission,
  request: Request
): Promise<ValidationResult> {
  const checks = await Promise.all([
    checkHoneypot(submission),
    checkRateLimit(request.ip),
    checkUserTrustScore(submission.userId),
    // Optional: checkRecaptcha(submission.recaptchaToken)
  ]);

  const spamScore = checks.reduce((score, check) => {
    return score + (check.isSpam ? check.confidence : 0);
  }, 0) / checks.length;

  return {
    allowed: spamScore < 0.5,
    requiresModeration: spamScore >= 0.3 && spamScore < 0.5,
    spamScore,
    failedChecks: checks.filter(c => c.isSpam).map(c => c.reason)
  };
}
```

---

## 4. OAuth Trust Signals Integration

### Provider Trust Hierarchy

Different OAuth providers offer varying levels of identity assurance:

| Provider | Trust Level | Rationale |
|----------|-------------|-----------|
| Google | High | Strong verification, hard to create fake accounts |
| Apple | High | Requires device + Apple ID verification |
| Microsoft | High | Enterprise-grade identity |
| GitHub | Medium-High | Requires email verification, developer-focused |
| Facebook | Medium | Large spam problem, but identity linked |
| Twitter/X | Medium | Phone verification optional |
| Discord | Low-Medium | Easy to create accounts |
| Email/Password | Low | No third-party verification |

### Extracting Trust Signals from OAuth

```typescript
interface OAuthTrustSignals {
  provider: string;
  emailVerified: boolean;
  accountAge?: Date;
  profileComplete: boolean;
  hasTwoFactor?: boolean;
}

function extractGoogleTrustSignals(profile: GoogleProfile): OAuthTrustSignals {
  return {
    provider: 'google',
    emailVerified: profile.email_verified ?? false,
    profileComplete: !!(profile.name && profile.picture),
    // Google doesn't expose account age, but verified email is strong signal
  };
}

function extractGitHubTrustSignals(profile: GitHubProfile): OAuthTrustSignals {
  return {
    provider: 'github',
    emailVerified: profile.email !== null, // GitHub only returns verified emails
    accountAge: new Date(profile.created_at),
    profileComplete: !!(profile.name && profile.bio),
    hasTwoFactor: profile.two_factor_authentication
  };
}
```

### OAuth-Based Rate Limit Adjustments

```typescript
function getOAuthAdjustedRateLimits(
  baseLimit: number,
  oauthSignals: OAuthTrustSignals
): number {
  let multiplier = 1.0;

  // Provider trust bonus
  const providerMultipliers: Record<string, number> = {
    'google': 1.5,
    'apple': 1.5,
    'github': 1.4,
    'microsoft': 1.4,
    'facebook': 1.2,
    'twitter': 1.2,
    'discord': 1.1,
  };

  multiplier *= providerMultipliers[oauthSignals.provider] ?? 1.0;

  // Additional bonuses
  if (oauthSignals.emailVerified) multiplier *= 1.1;
  if (oauthSignals.hasTwoFactor) multiplier *= 1.2;
  if (oauthSignals.profileComplete) multiplier *= 1.05;

  // Account age bonus (for providers that expose it)
  if (oauthSignals.accountAge) {
    const ageInDays = (Date.now() - oauthSignals.accountAge.getTime()) / (1000 * 60 * 60 * 24);
    if (ageInDays > 365) multiplier *= 1.3;
    else if (ageInDays > 90) multiplier *= 1.15;
  }

  return Math.floor(baseLimit * multiplier);
}
```

### Security Considerations (2025-2026 Threats)

Recent research highlights OAuth device code phishing as a growing threat. Key defensive measures:

1. **Block device code flow for standard users** unless explicitly required
2. **Monitor consent events** - unusual app consents are high-priority signals
3. **Verify publisher badges** - Microsoft's blue verified badge indicates vetted apps
4. **Don't trust OAuth tokens indefinitely** - implement token refresh monitoring

```typescript
// Monitor for suspicious OAuth patterns
interface OAuthSecurityCheck {
  isNewDevice: boolean;
  isUnusualLocation: boolean;
  consentGrantedRecently: boolean;
  unusualPermissionScope: boolean;
}

function assessOAuthRisk(check: OAuthSecurityCheck): 'low' | 'medium' | 'high' {
  const riskFactors = [
    check.isNewDevice,
    check.isUnusualLocation,
    check.consentGrantedRecently,
    check.unusualPermissionScope
  ].filter(Boolean).length;

  if (riskFactors >= 3) return 'high';
  if (riskFactors >= 2) return 'medium';
  return 'low';
}
```

---

## 5. Industry Standards for UGC Spam Prevention

### The Hybrid Approach (2025-2026 Consensus)

The industry standard is a combination of:

1. **AI/ML for scale** - Handle high volumes, detect patterns
2. **Human moderation** - Handle nuance, context, edge cases
3. **Community reporting** - Leverage user vigilance
4. **Automated rules** - Quick wins for obvious spam

### Content Moderation Pipeline

```
User Submission
      │
      ▼
┌─────────────────┐
│ Pre-Submission  │  ← Rate limiting, honeypots, trust check
│    Filters      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI/ML Scan    │  ← Spam detection, toxicity, etc.
│                 │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 Auto-      Queue for
Approve    Human Review
    │         │
    ▼         ▼
Published  Moderator
           Decision
              │
         ┌────┴────┐
         │         │
         ▼         ▼
      Approve    Reject
         │         │
         ▼         ▼
     Published  Notify User
```

### Key Metrics to Track

```typescript
interface ModerationMetrics {
  // Volume metrics
  submissionsPerHour: number;
  autoApprovalRate: number;
  manualReviewRate: number;

  // Quality metrics
  falsePositiveRate: number;  // Legitimate content flagged as spam
  falseNegativeRate: number;  // Spam that got through

  // Performance metrics
  avgReviewTimeMs: number;
  queueBacklogSize: number;

  // Trust metrics
  newUserSpamRate: number;
  establishedUserSpamRate: number;
}
```

### Community Guidelines Best Practices

Per industry research, effective guidelines should:

- Be written in **plain language** (not legal jargon)
- Include **concrete examples** of violations
- Be **prominently displayed** (not buried in footers)
- Have **clear consequences** for violations
- Be **consistently enforced**

### Recommended Tooling Stack

| Function | Options |
|----------|---------|
| Rate Limiting | Redis + custom logic, Cloudflare, AWS WAF |
| Spam Detection | Akismet, CleanTalk, OOPSpam, custom ML |
| Content Moderation | AWS Rekognition, Google Cloud Vision, Perspective API |
| CAPTCHA (backup) | hCaptcha, Cloudflare Turnstile, reCAPTCHA v3 |
| Abuse Monitoring | Sift, Castle, custom dashboards |

---

## 6. Recommended Implementation Strategy

### Phase 1: Foundation (Week 1-2)

1. **Implement sliding window rate limiting** with Redis
2. **Add honeypot fields** to all public forms
3. **Set up basic trust scoring** based on account age + verification status
4. **Configure response headers** for rate limit communication

### Phase 2: OAuth Integration (Week 3)

1. **Extract trust signals** from OAuth providers
2. **Adjust rate limits** based on OAuth trust level
3. **Implement OAuth security monitoring** for suspicious patterns

### Phase 3: Advanced Trust (Week 4+)

1. **Build content history tracking** for trust score evolution
2. **Implement progressive privilege unlocking**
3. **Set up moderation queue** with AI pre-filtering
4. **Create admin dashboard** for metrics and manual review

### Quick Wins (Implement Immediately)

```typescript
// Minimum viable anti-spam for day 1
const QUICK_WIN_CONFIG = {
  // Global rate limits
  globalRateLimit: {
    windowMs: 60 * 1000,  // 1 minute
    maxRequests: 100
  },

  // Strict limits for new users (< 7 days old)
  newUserLimits: {
    postsPerDay: 3,
    commentsPerDay: 10,
    requireModeration: true
  },

  // Honeypot field name
  honeypotFieldName: 'website',

  // Minimum form completion time
  minFormTimeMs: 2000,

  // Trust score threshold for auto-approval
  autoApprovalThreshold: 60
};
```

---

## Sources

### Rate Limiting
- [Cloudflare WAF Rate Limiting Best Practices](https://developers.cloudflare.com/waf/rate-limiting-rules/best-practices/)
- [API7 - Rate Limiting Guide: Algorithms & Best Practices](https://api7.ai/blog/rate-limiting-guide-algorithms-best-practices)
- [Postman - What is API Rate Limiting?](https://blog.postman.com/what-is-api-rate-limiting/)
- [AlgoMaster - Rate Limiting Algorithms Explained with Code](https://blog.algomaster.io/p/rate-limiting-algorithms-explained-with-code)
- [Tyk - API Rate Limiting Explained](https://tyk.io/learning-center/api-rate-limiting-explained-from-basics-to-best-practices/)

### Trust Scoring
- [Sift Digital Trust Index Q2 2025](https://sift.com/index-reports-ai-fraud-q2-2025/)
- [DataDome - reCAPTCHA v3 Score](https://datadome.co/anti-detect-tools/recaptha-score/)
- [Stanford/Yahoo - TrustRank Algorithm (PDF)](https://www.vldb.org/conf/2004/RS15P3.PDF)

### Honeypots
- [WorkOS - Stop Bots with Honeypots](https://workos.com/blog/stop-bots-with-honeypots)
- [Nikolai Lehbrink - Prevent AI Bots from Spamming Forms](https://www.nikolailehbr.ink/blog/prevent-form-spamming-honeypot/)
- [DEV Community - Simple Honeypot Tutorial](https://dev.to/felipperegazio/how-to-create-a-simple-honeypot-to-protect-your-web-forms-from-spammers--25n8)
- [Spatie Laravel Honeypot](https://github.com/spatie/laravel-honeypot)

### OAuth Security
- [Microsoft Entra Blog - OAuth Consent Phishing](https://techcommunity.microsoft.com/blog/microsoft-entra-blog/oauth-consent-phishing-explained-and-prevented/4423357)
- [Proofpoint - Device Code Authorization Phishing](https://www.proofpoint.com/us/blog/threat-insight/access-granted-phishing-device-code-authorization-account-takeover)
- [Elastic Security Labs - Entra ID OAuth Phishing Detection](https://www.elastic.co/security-labs/entra-id-oauth-phishing-detection)

### UGC Industry Standards
- [WebPurify - Content Moderation Definitive Guide 2025](https://www.webpurify.com/blog/content-moderation-definitive-guide/)
- [Utopia Analytics - UGC Moderation Guide](https://www.utopiaanalytics.com/article/user-generated-content-moderation)
- [ACM - Scaling Content Moderation for Massive Datasets](https://cacm.acm.org/blogcacm/the-ugc-overload-scaling-content-moderation-for-massive-datasets/)
