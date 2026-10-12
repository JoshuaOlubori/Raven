import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from '@tanstack/react-router';
import { AlertCircle, Building2, Clock, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useAuthStore } from '@/lib/auth-store';
import { useLogin } from '@/lib/hooks';
import { cn } from '@/lib/utils';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  rememberOperatory: z.boolean().optional(),
});

type LoginForm = z.infer<typeof loginSchema>;

export function SignInPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const loginMutation = useLogin();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      rememberOperatory: false,
    },
  });

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    try {
      const result = await loginMutation.mutateAsync({
        email: data.email,
        password: data.password,
      });

      // Fetch user details after login
      const userResponse = await fetch('/api/v1/auth/me', {
        headers: {
          Authorization: `Bearer ${result.accessToken}`,
        },
      });

      if (userResponse.ok) {
        const user = await userResponse.json();
        setAuth(result.accessToken, user);
        navigate({ to: '/today' });
      } else {
        setError('Failed to load user profile');
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Invalid email or password');
      }
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel - Brand */}
      <div className="hidden lg:flex lg:w-1/2 bg-brand-primary text-brand-on-primary flex-col items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-primary via-brand-primary to-primary-container" />
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage:
              'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cpath d="M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z" fill="currentColor" fill-rule="nonzero"/%3E%3C/g%3E%3C/svg%3E")',
          }}
        />

        <div className="relative z-10 max-w-md w-full text-center">
          <div className="flex items-center justify-center gap-3 mb-8">
            <Building2 className="w-12 h-12" />
            <span className="text-3xl font-bold">Raven Dental</span>
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold mb-6 leading-tight">
            Internal Operations Portal
          </h1>
          <p className="text-lg opacity-90 mb-12 max-w-lg mx-auto">
            Secure access for clinic staff. Manage patients, appointments, schedules, and clinical
            operations from a single platform.
          </p>

          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <div className="text-3xl font-bold">24/7</div>
              <div className="text-sm opacity-80">Access</div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <div className="text-3xl font-bold">HIPAA</div>
              <div className="text-sm opacity-80">Compliant</div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <div className="text-3xl font-bold">Real-time</div>
              <div className="text-sm opacity-80">Updates</div>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-white/20">
            <p className="text-sm opacity-60">Suite 400 • Downtown Clinic • Internal Use Only</p>
          </div>
        </div>
      </div>

      {/* Right panel - Sign in form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-bg-canvas">
        <div className="w-full max-w-md">
          <div className="text-center mb-8 lg:hidden">
            <Link
              to="/sign-in"
              className="inline-flex items-center gap-2 text-brand-primary font-bold text-xl"
            >
              <Building2 className="w-8 h-8" />
              Raven Dental
            </Link>
          </div>

          <div className="bg-bg-card rounded-2xl shadow-elev-1 p-8 border border-border-subtle">
            <div className="text-center mb-8">
              <h2 className="text-headline-lg text-text-primary mb-2">Welcome back</h2>
              <p className="text-text-secondary text-body-md">
                Sign in to access the operations portal
              </p>
            </div>

            {error && (
              <div
                className="mb-6 flex items-center gap-3 p-4 rounded-lg bg-status-error-bg text-status-error border border-status-error/20"
                role="alert"
              >
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-label-md text-text-primary mb-2">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...register('email')}
                    type="email"
                    id="email"
                    autoComplete="email"
                    placeholder="name@ravendental.internal"
                    className={cn(
                      'w-full pl-10 pr-4 py-3 rounded-lg border bg-bg-card text-text-primary placeholder-text-muted transition-colors',
                      errors.email
                        ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                        : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                    )}
                    disabled={isSubmitting}
                    aria-invalid={errors.email ? 'true' : 'false'}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                  />
                </div>
                {errors.email && (
                  <p
                    id="email-error"
                    className="mt-1.5 text-sm text-status-error flex items-center gap-1"
                  >
                    <AlertCircle className="w-3.5 h-3.5" />
                    {errors.email.message}
                  </p>
                )}
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="block text-label-md text-text-primary mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...register('password')}
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    className={cn(
                      'w-full pl-10 pr-12 py-3 rounded-lg border bg-bg-card text-text-primary placeholder-text-muted transition-colors',
                      errors.password
                        ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                        : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                    )}
                    disabled={isSubmitting}
                    aria-invalid={errors.password ? 'true' : 'false'}
                    aria-describedby={errors.password ? 'password-error' : undefined}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && (
                  <p
                    id="password-error"
                    className="mt-1.5 text-sm text-status-error flex items-center gap-1"
                  >
                    <AlertCircle className="w-3.5 h-3.5" />
                    {errors.password.message}
                  </p>
                )}
              </div>

              {/* Operatory selection (local preference) */}
              <div>
                <label htmlFor="operatory" className="block text-label-md text-text-primary mb-2">
                  Default Operatory (local preference)
                </label>
                <select
                  {...register('rememberOperatory')}
                  id="operatory"
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                  disabled={isSubmitting}
                >
                  <option value="">Auto-assign</option>
                  <option value="operatory-1">Operatory 1</option>
                  <option value="operatory-2">Operatory 2</option>
                  <option value="operatory-3">Operatory 3</option>
                  <option value="operatory-4">Operatory 4</option>
                  <option value="operatory-5">Operatory 5</option>
                  <option value="hygiene-1">Hygiene 1</option>
                  <option value="hygiene-2">Hygiene 2</option>
                  <option value="front-desk">Front Desk</option>
                </select>
                <p className="mt-1.5 text-xs text-text-muted">
                  Stored locally only — not sent to the server
                </p>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 px-4 rounded-full bg-brand-primary text-brand-on-primary font-semibold text-body-md hover:bg-brand-primary-hover focus:ring-2 focus:ring-brand-primary focus:ring-offset-2 focus:ring-offset-bg-card transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <svg
                      className="animate-spin w-5 h-5"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Signing in…
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>

            <div className="mt-6 pt-6 border-t border-border-subtle">
              <p className="text-center text-sm text-text-muted">
                Need help? Contact
                <span className="font-medium text-text-primary">
                  {' '}
                  Downtown Clinic Administrator
                </span>
                or <span className="font-medium text-text-primary">Front Desk Lead</span>
              </p>
            </div>
          </div>

          {/* Clock - hidden on mobile, shown on desktop */}
          <div className="hidden lg:block mt-8 text-center">
            <LiveClock />
          </div>
        </div>
      </div>
    </div>
  );
}

/** Live clock component */
function LiveClock() {
  const [time, setTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString('en-US', {
          timeZone: 'America/New_York',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: true,
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-bg-elevated border border-border-subtle">
      <Clock className="w-4 h-4 text-text-muted" />
      <span className="font-mono text-body-md text-text-secondary tabular-nums">{time}</span>
      <span className="text-xs text-text-muted uppercase tracking-wider">EDT</span>
    </div>
  );
}
