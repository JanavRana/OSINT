import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useRef, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Terminal, ShieldCheck, ArrowRight, KeyRound,
  Eye, EyeOff, RefreshCw, CheckCircle2, Loader2,
} from "lucide-react";
import { useSignup, useVerifyOtp, useLogin, useResendOtp } from "@/hooks/use-auth";
import { isAuthenticated } from "@/lib/auth";

export const Route = createFileRoute("/auth")({
  head: () => ({ meta: [{ title: "Sign In — IntelWeave" }] }),
  component: Auth,
});

type Step = "mode" | "otp";
type Mode = "login" | "signup";

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

  useEffect(() => {
    if (isAuthenticated()) nav({ to: "/dashboard" });
  }, [nav]);

  const [mode, setMode] = useState<Mode>("login");
  const [step, setStep] = useState<Step>("mode");
  const [email, setEmail] = useState("");
  const [pendingEmail, setPendingEmail] = useState("");
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

  return (
    <div className="min-h-screen relative flex items-center justify-center p-4 bg-background text-foreground grid-bg font-sans">
      <div className="relative grid md:grid-cols-2 gap-6 max-w-4xl w-full">
        {/* Brand pane */}
        <div className="hidden md:flex flex-col justify-between p-6 bg-surface border border-border rounded-md">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-sm bg-primary/10 border border-primary/40 text-primary grid place-items-center">
              <Terminal className="h-4 w-4" />
            </div>
            <div>
              <div className="font-display font-bold text-sm tracking-wider">INTELWEAVE</div>
              <div className="text-[9px] font-mono tracking-widest text-muted-foreground uppercase">Tactical Intelligence Console</div>
            </div>
          </div>

          <div className="space-y-3 font-mono">
            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm bg-surface-2 border border-border text-[10px] text-muted-foreground">
              <ShieldCheck className="h-3 w-3 text-success" /> TLP:AMBER AUTHENTICATION REQUIRED
            </div>
            <h1 className="text-2xl font-display font-bold tracking-tight font-sans">
              High-Density OSINT <span className="text-primary">Analysis Engine</span>
            </h1>
            <p className="text-xs font-sans text-muted-foreground leading-relaxed">
              Consolidate domains, email hashes, IP nodes, and crypto addresses into interactive graph topology.
            </p>
          </div>

          <div className="text-[10px] font-mono text-muted-foreground flex justify-between border-t border-border/60 pt-3">
            <span>SECURE SYSTEM ACCESS</span>
            <span>BUILD v4.1.0</span>
          </div>
        </div>

        {/* Form pane */}
        <Card className="p-6 border-border bg-surface rounded-md">
          <div className="md:hidden flex items-center gap-2 mb-4">
            <div className="h-7 w-7 rounded-sm bg-primary/10 border border-primary/40 text-primary grid place-items-center">
              <Terminal className="h-3.5 w-3.5" />
            </div>
            <span className="font-display font-bold text-sm">INTELWEAVE</span>
          </div>

          {step === "otp" ? (
            <>
              <div className="flex items-center gap-2 mb-1">
                <div className="h-6 w-6 rounded-sm bg-success/10 border border-success/30 text-success grid place-items-center">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                </div>
                <h2 className="text-sm font-display font-bold uppercase tracking-wider text-foreground">Verify OTP Authentication</h2>
              </div>
              <p className="text-xs font-mono text-muted-foreground mt-1 mb-4">
                Code sent to <span className="text-foreground font-bold">{pendingEmail}</span>.
              </p>

              <form onSubmit={handleVerifyOtp} className="space-y-4 font-mono">
                <div>
                  <Label className="sr-only">One-time code</Label>
                  <div className="flex gap-1.5 justify-center" onPaste={handleOtpPaste}>
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
                        className="h-10 w-10 rounded-sm border border-border bg-surface-2 text-center text-lg font-bold text-foreground focus:outline-none focus:border-primary transition"
                      />
                    ))}
                  </div>

                  <div className="mt-2 text-center text-[10px] text-muted-foreground">
                    {countdown.expired
                      ? <span className="text-destructive font-bold">CODE EXPIRED</span>
                      : <span>EXPIRES IN <strong className="text-foreground">{countdown.display}</strong></span>
                    }
                  </div>
                </div>

                {currentError && (
                  <p role="alert" className="text-xs text-destructive text-center bg-destructive/10 border border-destructive/30 rounded-sm p-1.5">{currentError.message}</p>
                )}

                <Button
                  type="submit"
                  disabled={otp.join("").length < 6 || verifyOtp.isPending}
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-mono gap-1.5 h-8"
                >
                  {verifyOtp.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                  VERIFY & SIGN IN
                </Button>

                <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                  Didn't receive code?
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={resendOtp.isPending}
                    className="text-primary hover:underline flex items-center gap-1 font-mono disabled:opacity-50"
                  >
                    <RefreshCw className="h-3 w-3" />
                    {resendOtp.isPending ? "Sending…" : "Resend"}
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => { setStep("mode"); setOtp(["", "", "", "", "", ""]); }}
                  className="w-full text-xs text-muted-foreground hover:text-foreground text-center"
                >
                  ← Return to registration
                </button>
              </form>
            </>
          ) : (
            <>
              <h2 className="text-sm font-display font-bold uppercase tracking-wider text-foreground">
                {mode === "login" ? "Analyst Authentication" : "Register Analyst Account"}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {mode === "login"
                  ? "Enter authorized credentials to access workspace"
                  : "Provision a new investigator account"}
              </p>

              <form
                className="mt-4 space-y-3 font-mono text-xs"
                onSubmit={mode === "login" ? handleLogin : handleSignup}
              >
                {mode === "signup" && (
                  <div>
                    <Label htmlFor="full-name" className="text-[10px] text-muted-foreground uppercase">Full Name</Label>
                    <Input
                      id="full-name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Analyst Name"
                      autoComplete="name"
                      className="mt-1 bg-surface-2 border-border text-xs h-8"
                      required
                    />
                  </div>
                )}

                <div>
                  <Label htmlFor="email" className="text-[10px] text-muted-foreground uppercase">Analyst Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="analyst@agency.gov"
                    autoComplete="email"
                    className="mt-1 bg-surface-2 border-border text-xs h-8"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="password" className="text-[10px] text-muted-foreground uppercase">Access Key / Password</Label>
                  <div className="relative mt-1">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete={mode === "login" ? "current-password" : "new-password"}
                      className="bg-surface-2 border-border text-xs h-8 pr-8"
                      minLength={mode === "signup" ? 8 : undefined}
                      required
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>

                {currentError && (
                  <div role="alert" className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-sm p-1.5">{currentError.message}</div>
                )}

                <Button
                  type="submit"
                  disabled={signup.isPending || login.isPending}
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90 gap-1.5 font-mono text-xs h-8"
                >
                  {(signup.isPending || login.isPending) ? (
                    <><Loader2 className="h-3.5 w-3.5 animate-spin" /> AUTHENTICATING…</>
                  ) : mode === "login" ? (
                    <>SIGN IN <ArrowRight className="h-3.5 w-3.5" /></>
                  ) : (
                    <>PROVISION ACCOUNT <KeyRound className="h-3.5 w-3.5" /></>
                  )}
                </Button>
              </form>

              <div className="mt-4 text-center text-xs text-muted-foreground font-mono">
                {mode === "login" ? (
                  <>Need an analyst account?{" "}
                    <button onClick={() => { setMode("signup"); signup.reset(); login.reset(); }} className="text-primary hover:underline font-bold">
                      REGISTER
                    </button>
                  </>
                ) : (
                  <>Existing analyst?{" "}
                    <button onClick={() => { setMode("login"); signup.reset(); login.reset(); }} className="text-primary hover:underline font-bold">
                      SIGN IN
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

