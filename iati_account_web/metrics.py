from prometheus_client import Counter, Gauge

PROM_OIDC_POSTLOGIN_COUNTER = Counter("iatiaccount_oidc_postlogin_total", "Total number of successful OIDC logins#")

PROM_OIDC_LOGOUT_COUNTER = Counter("iatiaccount_oidc_logout_total", "Total number of OIDC logouts")

PROM_USER_PROVISIONING_COUNTER = Counter(
    "iatiaccount_user_provisioning_total",
    "Total number of provisioning, by state",
    ["state"],
)

PROM_USER_PROVISIONING_GAUGE = Gauge(
    "iatiaccount_user_provisioning_state_total",
    "Total number of provisioning users",
)
