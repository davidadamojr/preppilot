'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { useAvailableExclusions } from '@/hooks/use-available-exclusions';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [dietType, setDietType] = useState('low_histamine');
  const [selectedExclusions, setSelectedExclusions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  // Use cached exclusions - shared across register page and settings
  const { exclusions: availableExclusions, isLoading: isLoadingExclusions } = useAvailableExclusions();

  const toggleExclusion = (value: string) => {
    setSelectedExclusions((prev) =>
      prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      toast({
        title: 'Passwords do not match',
        description: 'Please make sure your passwords match',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      await register(email, password, dietType, selectedExclusions);
      router.push('/dashboard');
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Registration failed';
      toast({
        title: 'Registration failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main id="main-content" className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">Create an account</CardTitle>
          <CardDescription>
            Start your meal prep journey with PrepPilot
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dietType">Diet Type</Label>
              <select
                id="dietType"
                value={dietType}
                onChange={(e) => setDietType(e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="low_histamine">Low Histamine</option>
                <option value="low_histamine_low_oxalate">Low Histamine & Low Oxalate</option>
                <option value="fodmap">Low FODMAP</option>
                <option value="fructose_free">Fructose Free</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Dietary Exclusions (Optional)</Label>
              <p className="text-xs text-gray-500 mb-2">
                Select any ingredients or categories you want to exclude from your meal plans
              </p>
              <div className="max-h-48 overflow-y-auto border rounded-md p-3 space-y-2">
                {isLoadingExclusions ? (
                  <div className="flex items-center justify-center py-4">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-600"></div>
                  </div>
                ) : (
                  availableExclusions.map((exclusion) => (
                    <label
                      key={exclusion.value}
                      className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-1 rounded"
                    >
                      <input
                        type="checkbox"
                        checked={selectedExclusions.includes(exclusion.value)}
                        onChange={() => toggleExclusion(exclusion.value)}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                      <span className="text-sm">{exclusion.name}</span>
                    </label>
                  ))
                )}
              </div>
              {selectedExclusions.length > 0 && (
                <p className="text-xs text-gray-600 mt-2">
                  {selectedExclusions.length} exclusion(s) selected
                </p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Creating account...' : 'Create account'}
            </Button>
            <p className="text-sm text-center text-gray-600">
              Already have an account?{' '}
              <Link href="/login" className="text-blue-600 hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </main>
  );
}
