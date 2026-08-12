import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useRef, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Radar, ShieldCheck, ArrowRight, KeyRound,
  Eye, EyeOff, RefreshCw, CheckCircle2, Loader2,
} from "lucide-react";
import { useSignup, useVerifyOtp, useLogin, useResendOtp } from "@/hooks/use-auth";
import { isAuthenticated } from "@/lib/auth";

export const Route = createFileRoute("/auth")({
  head: () => ({ meta: [{ title: "Sign in — Intel Weave" }] }),
  component: Auth,
});

type Step = "mode" | "otp";
type Mode = "login" | "signup";

/** OTP Countdown — counts down from 5:00 */
function useCountdown(active: boolean) {
  const [seconds, setSeconds] = useState(300);
  useEffect(() => {
    if (!active) { setSeconds(300); return; }
    const id = setInterval(() => setSeconds((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [active]);
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return { display: `${mm}:${ss}`, expired: seconds === 0 };
}

function Auth() {
  const nav = useNavigate();

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated()) nav({ to: "/dashboard" });
  }, [nav]);

  const [mode, setMode] = useState<Mode>("login");
  const [step, setStep] = useState<Step>("mode");
  const [email, setEmail] = useState("");
  const [pendingEmail, setPendingEmail] = useState(""); // locked email during OTP step
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  const signup = useSignup();
  const verifyOtp = useVerifyOtp();
  const login = useLogin();
  const resendOtp = useResendOtp();
  const countdown = useCountdown(step === "otp");

  // ── OTP digit input handling ──────────────────────────────────────────────

  const handleOtpChange = useCallback((idx: number, val: string) => {
    const digit = val.replace(/\D/g, "").slice(-1);
    setOtp((prev) => {
      const next = [...prev];
      next[idx] = digit;
      return next;
    });
    if (digit && idx < 5) {
      otpRefs.current[idx + 1]?.focus();
    }
  }, []);

  const handleOtpKeyDown = useCallback((idx: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      otpRefs.current[idx - 1]?.focus();
    }
  }, [otp]);

  const handleOtpPaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const digits = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    setOtp((prev) => {
      const next = [...prev];
      digits.split("").forEach((d, i) => { next[i] = d; });
      return next;
    });
    otpRefs.current[Math.min(digits.length, 5)]?.focus();
  }, []);

  // ── Submit handlers ───────────────────────────────────────────────────────

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !fullName || !password) return;
    try {
      await signup.mutate({ email: email.trim(), fullName: fullName.trim(), password });
      setPendingEmail(email.trim());
      setStep("otp");
    } catch { /* error shown via signup.error */ }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    try {
      await login.mutate({ email: email.trim(), password });
      nav({ to: "/dashboard" });
    } catch { /* error shown via login.error */ }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    const code = otp.join("");
    if (code.length < 6) return;
    try {
      await verifyOtp.mutate({ email: pendingEmail, otp: code });
      nav({ to: "/dashboard" });
    } catch { /* error shown via verifyOtp.error */ }
  }

  async function handleResend() {
    try {
      await resendOtp.mutate({ email: pendingEmail });
      setOtp(["", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    } catch { /* ignore */ }
  }

  const currentError = step === "otp"
    ? verifyOtp.error || resendOtp.error
    : mode === "login" ? login.error : signup.error;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 grid-bg opacity-40" />
      <div className="absolute -top-40 -left-40 h-[520px] w-[520px] rounded-full bg-primary/25 blur-[120px] float" />
      <div className="absolute -bottom-40 -right-40 h-[520px] w-[520px] rounded-full bg-accent/25 blur-[120px] float" />

      <div className="relative grid md:grid-cols-2 gap-8 max-w-5xl w-full">
        {/* Brand pane */}
        <div className="hidden md:flex flex-col justify-between p-8">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-primary to-accent grid place-items-center shadow-[0_0_30px_-4px_var(--primary)]">
              <Radar className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <div className="font-display font-bold text-xl">Intel Weave</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">OSINT Intelligence Aggregator</div>
            </div>
          </div>

          <div className="space-y-4">
            <h1 className="text-4xl font-display font-bold tracking-tight">
              Investigate <span className="gradient-text">at the speed of intent.</span>
            </h1>
            <p className="text-sm text-muted-foreground max-w-md">
              Unify emails, wallets, domains and social identifiers into a single graph.
              Purpose-built for cybercrime investigators and analysts.
            </p>
          </div>

          <div className="text-xs text-muted-foreground">© Intel Weave · v3.2</div>
        </div>

        {/* Form pane */}
        <Card className="glass border-border/60 p-8 relative overflow-hidden">
          {/* Mobile logo */}
          <div className="md:hidden flex items-center gap-2 mb-6">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-accent grid place-items-center">
              <Radar className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-display font-bold">Intel Weave</span>
          </div>

          {/* ── OTP Step ──────────────────────────────────────────────── */}
          {step === "otp" ? (
            <>
              <div className="flex items-center gap-2 mb-1">
                <div className="h-8 w-8 rounded-full bg-success/15 grid place-items-center">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                </div>
                <h2 className="text-2xl font-display font-semibold">Verify your email</h2>
              </div>
              <p className="text-sm text-muted-foreground mt-1 mb-6">
                We sent a 6-digit code to <span className="text-foreground font-medium">{pendingEmail}</span>.
                Check your server logs for the OTP code.
              </p>

              <form onSubmit={handleVerifyOtp} className="space-y-5">
                {/* OTP input cells */}
                <div>
                  <Label className="sr-only">One-time code</Label>
                  <div className="flex gap-2 justify-center" onPaste={handleOtpPaste}>
                    {otp.map((digit, i) => (
                      <input
                        key={i}
                        ref={(el) => { otpRefs.current[i] = el; }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleOtpChange(i, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(i, e)}
                        aria-label={`OTP digit ${i + 1}`}
                        className="h-12 w-12 rounded-xl border border-border/60 bg-surface/60 text-center text-xl font-mono font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/60 focus:border-primary/60 transition caret-transparent"
                      />
                    ))}
                  </div>

                  {/* Countdown */}
                  <div className="mt-2 text-center text-xs text-muted-foreground">
                    {countdown.expired
                      ? <span className="text-destructive">Code expired</span>
                      : <span>Expires in <span className="font-mono text-foreground">{countdown.display}</span></span>
                    }
                  </div>
                </div>

                {currentError && (
                  <p role="alert" className="text-xs text-destructive text-center">{currentError.message}</p>
                )}

                <Button
                  type="submit"
                  disabled={otp.join("").length < 6 || verifyOtp.isPending}
                  className="w-full bg-gradient-to-r from-primary to-accent text-primary-foreground gap-2"
                >
                  {verifyOtp.isPending
                    ? <><Loader2 className="h-4 w-4 animate-spin" /> Verifying…</>
                    : <><CheckCircle2 className="h-4 w-4" /> Verify & Sign in</>
                  }
                </Button>

                <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                  Didn't receive it?
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={resendOtp.isPending}
                    className="text-primary hover:underline flex items-center gap-1 disabled:opacity-50"
                  >
                    <RefreshCw className="h-3 w-3" />
                    {resendOtp.isPending ? "Sending…" : "Resend code"}
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => { setStep("mode"); setOtp(["", "", "", "", "", ""]); }}
                  className="w-full text-xs text-muted-foreground hover:text-foreground transition text-center"
                >
                  ← Back to sign up
                </button>
              </form>
            </>
          ) : (
            /* ── Login / Signup Step ──────────────────────────────────── */
            <>
              <h2 className="text-2xl font-display font-semibold">
                {mode === "login" ? "Welcome back" : "Create your account"}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                {mode === "login"
                  ? "Sign in to continue your investigations."
                  : "Provision an analyst account with credentials."}
              </p>

              <form
                className="mt-6 space-y-4"
                onSubmit={mode === "login" ? handleLogin : handleSignup}
              >
                {mode === "signup" && (
                  <div>
                    <Label htmlFor="full-name">Full name</Label>
                    <Input
                      id="full-name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Mei Chen"
                      autoComplete="name"
                      className="mt-1.5 bg-surface/60"
                      required
                    />
                  </div>
                )}

                <div>
                  <Label htmlFor="email">Work email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@agency.gov"
                    autoComplete="email"
                    className="mt-1.5 bg-surface/60"
                    required
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                  </div>
                  <div className="relative mt-1.5">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete={mode === "login" ? "current-password" : "new-password"}
                      className="bg-surface/60 pr-10"
                      minLength={mode === "signup" ? 8 : undefined}
                      required
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {mode === "signup" && (
                    <p className="text-[10px] text-muted-foreground mt-1">Minimum 8 characters.</p>
                  )}
                </div>

                {currentError && (
                  <p role="alert" className="text-xs text-destructive">{currentError.message}</p>
                )}

                <Button
                  type="submit"
                  disabled={signup.isPending || login.isPending}
                  className="w-full bg-gradient-to-r from-primary to-accent text-primary-foreground gap-2"
                >
                  {(signup.isPending || login.isPending) ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> {mode === "login" ? "Signing in…" : "Creating account…"}</>
                  ) : mode === "login" ? (
                    <>Sign in <ArrowRight className="h-4 w-4" /></>
                  ) : (
                    <>Create account <KeyRound className="h-4 w-4" /></>
                  )}
                </Button>
              </form>

              <div className="mt-5 text-center text-xs text-muted-foreground">
                {mode === "login" ? (
                  <>Need an account?{" "}
                    <button onClick={() => { setMode("signup"); signup.reset(); login.reset(); }} className="text-primary hover:underline">
                      Sign up
                    </button>
                  </>
                ) : (
                  <>Have an account?{" "}
                    <button onClick={() => { setMode("login"); signup.reset(); login.reset(); }} className="text-primary hover:underline">
                      Sign in
                    </button>
                  </>
                )}
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
