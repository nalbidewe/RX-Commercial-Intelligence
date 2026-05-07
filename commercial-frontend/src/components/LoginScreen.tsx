// Production: "Continue with Microsoft" redirects to Azure Easy Auth → Azure AD.
// The app registration is scoped to the Riyadh Air tenant, so only
// @riyadhair.com / @vendor.riyadhair.com accounts can authenticate.
//
// Local dev: Easy Auth is not available, so the button calls onLocalDevBypass()
// to skip the auth gate and access the app directly.

interface LoginScreenProps {
  onLocalDevBypass: () => void;
}

function MicrosoftIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  );
}

export default function LoginScreen({ onLocalDevBypass }: LoginScreenProps) {
  function handleLogin() {
    if (import.meta.env.DEV) {
      // Local dev only — bypasses auth so the app can be tested without Easy Auth.
      onLocalDevBypass();
    } else {
      // Production — redirect to Azure Easy Auth; Azure AD enforces tenant-level
      // access so only Riyadh Air accounts can complete the flow.
      window.location.href = `/.auth/login/aad?post_login_redirect_uri=${encodeURIComponent('/commercial/')}`;
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="w-1/2 flex flex-col bg-white px-14 py-10">
        <img
          src={`${import.meta.env.BASE_URL}riyadh-air-logo.png`}
          alt="Riyadh Air"
          className="h-10 w-auto object-contain object-left"
        />

        <div className="flex-1 flex flex-col items-center justify-center gap-8">
          <img
            src={`${import.meta.env.BASE_URL}rx-logo-short.png`}
            alt="Riyadh Air"
            className="h-16 w-auto object-contain"
          />
          <p className="text-lg font-semibold text-rx-ink">
            Log in to Access the commercial intelligence app
          </p>
          <button
            type="button"
            onClick={handleLogin}
            className="flex items-center gap-3 border border-gray-300 rounded px-6 py-2.5 text-sm font-medium text-rx-ink hover:bg-gray-50 transition"
          >
            <MicrosoftIcon />
            Continue with Microsoft
          </button>

          {import.meta.env.DEV && (
            <p className="text-xs text-rx-subtle">
              Local dev mode — login is bypassed on click.
            </p>
          )}
        </div>
      </div>

      {/* Right panel — aircraft image */}
      <div className="w-1/2 relative overflow-hidden">
        <img
          src={`${import.meta.env.BASE_URL}aircraft.png`}
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
        />
      </div>
    </div>
  );
}
