export const appConfig = {
  appUrl: process.env.NEXT_PUBLIC_APP_URL || process.env.APP_URL || "http://localhost:3000",
  sessionCookieName: "suggest_monan_session",
  sessionSecret: process.env.SESSION_SECRET || "suggest-monan-dev-secret",
  jobSecret: process.env.JOB_SECRET || "suggest-monan-jobs",
  featureFlags: {
    smartPrefillEnabled: process.env.FEATURE_SMART_PREFILL_ENABLED !== "false",
    weightedVoteEnabled: process.env.FEATURE_WEIGHTED_VOTE_ENABLED !== "false",
    splitGroupEnabled: process.env.FEATURE_SPLIT_GROUP_ENABLED !== "false",
    exploreModeEnabled: process.env.FEATURE_EXPLORE_MODE_ENABLED !== "false",
    enterpriseDashboardEnabled: process.env.FEATURE_ENTERPRISE_DASHBOARD_ENABLED !== "false",
    fallbackRankerEnabled: process.env.FEATURE_FALLBACK_RANKER_ENABLED !== "false",
  },
  ranking: {
    algorithmVersion: "ranker-v1",
    configVersion: "config-v1",
    topVoteOptions: 3,
    maxCandidates: 30,
    mmrBeta: 0.8,
  },
};

