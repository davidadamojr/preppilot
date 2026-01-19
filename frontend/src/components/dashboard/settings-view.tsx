'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/auth-context';
import { authApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useAvailableExclusions } from '@/hooks/use-available-exclusions';
import { ExclusionsListSkeleton } from './skeletons';
import { DIET_TYPE_LABELS, DIET_TYPE_OPTIONS } from '@/lib/utils';

export function SettingsView() {
  const { user, updateExclusions, logout, refreshProfile } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedExclusions, setSelectedExclusions] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Use cached exclusions - shared across register page and settings
  const { exclusions: availableExclusions, isLoading, isError } = useAvailableExclusions();

  // Profile editing state
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editedFullName, setEditedFullName] = useState('');
  const [editedDietType, setEditedDietType] = useState('');
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Password change state
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSavingPassword, setIsSavingPassword] = useState(false);

  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  // Initialize selected exclusions from user data
  useEffect(() => {
    if (user?.dietary_exclusions) {
      setSelectedExclusions(user.dietary_exclusions);
    }
  }, [user?.dietary_exclusions]);

  // Show error toast if exclusions fail to load
  useEffect(() => {
    if (isError) {
      toast({
        title: 'Error',
        description: 'Failed to load dietary exclusion options',
        variant: 'destructive',
      });
    }
  }, [isError, toast]);

  // Track changes
  useEffect(() => {
    if (!user?.dietary_exclusions) return;

    const currentSet = new Set(user.dietary_exclusions);
    const selectedSet = new Set(selectedExclusions);

    const isDifferent =
      currentSet.size !== selectedSet.size ||
      Array.from(currentSet).some(item => !selectedSet.has(item));

    setHasChanges(isDifferent);
  }, [selectedExclusions, user?.dietary_exclusions]);

  const toggleExclusion = (value: string) => {
    setSelectedExclusions((prev) =>
      prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value]
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateExclusions(selectedExclusions);
      toast({
        title: 'Settings saved',
        description: 'Your dietary exclusions have been updated',
      });
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to update exclusions:', error);
      toast({
        title: 'Error',
        description: 'Failed to save your dietary exclusions',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (user?.dietary_exclusions) {
      setSelectedExclusions(user.dietary_exclusions);
    }
  };

  const formatDate = (dateString: string) => {
    // Parse as local time to avoid timezone shift
    // new Date("2025-01-04") interprets as UTC, which shifts dates in western timezones
    const [year, month, day] = dateString.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Profile editing handlers
  const startEditingProfile = () => {
    setEditedFullName(user?.full_name || '');
    setEditedDietType(user?.diet_type || 'low_histamine');
    setIsEditingProfile(true);
  };

  const cancelEditingProfile = () => {
    setIsEditingProfile(false);
    setEditedFullName('');
    setEditedDietType('');
  };

  const handleSaveProfile = async () => {
    setIsSavingProfile(true);
    try {
      await authApi.updateProfile({
        full_name: editedFullName || undefined,
        diet_type: editedDietType,
      });
      await refreshProfile();
      toast({
        title: 'Profile updated',
        description: 'Your profile has been successfully updated',
      });
      setIsEditingProfile(false);
    } catch (error) {
      console.error('Failed to update profile:', error);
      toast({
        title: 'Error',
        description: 'Failed to update your profile',
        variant: 'destructive',
      });
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Password change handlers
  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      toast({
        title: 'Error',
        description: 'New passwords do not match',
        variant: 'destructive',
      });
      return;
    }

    if (newPassword.length < 8) {
      toast({
        title: 'Error',
        description: 'New password must be at least 8 characters',
        variant: 'destructive',
      });
      return;
    }

    setIsSavingPassword(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      toast({
        title: 'Password changed',
        description: 'Your password has been successfully changed',
      });
      setIsChangingPassword(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: unknown) {
      console.error('Failed to change password:', error);
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast({
        title: 'Error',
        description: axiosError.response?.data?.detail || 'Failed to change your password',
        variant: 'destructive',
      });
    } finally {
      setIsSavingPassword(false);
    }
  };

  const cancelChangePassword = () => {
    setIsChangingPassword(false);
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  // Delete account handlers
  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') {
      toast({
        title: 'Error',
        description: 'Please type DELETE to confirm account deletion',
        variant: 'destructive',
      });
      return;
    }

    setIsDeleting(true);
    try {
      await authApi.deleteAccount();
      toast({
        title: 'Account deleted',
        description: 'Your account has been permanently deleted',
      });
      // Clear all cached user data to prevent data leakage
      queryClient.clear();
      logout();
      router.push('/login');
    } catch (error) {
      console.error('Failed to delete account:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete your account',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDeleteAccount = () => {
    setShowDeleteConfirm(false);
    setDeleteConfirmText('');
  };

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-6" role="region" aria-label="Account Settings">
      {/* Profile Information */}
      <Card aria-describedby="profile-desc">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Profile</CardTitle>
            <CardDescription id="profile-desc">Your account information</CardDescription>
          </div>
          {!isEditingProfile && (
            <Button variant="outline" size="sm" onClick={startEditingProfile}>
              Edit Profile
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditingProfile ? (
            <div className="space-y-4">
              <div>
                <label htmlFor="fullName" className="text-sm font-medium text-gray-500 block mb-1">
                  Full Name
                </label>
                <input
                  id="fullName"
                  type="text"
                  value={editedFullName}
                  onChange={(e) => setEditedFullName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter your full name"
                />
              </div>
              <div>
                <label htmlFor="dietType" className="text-sm font-medium text-gray-500 block mb-1">
                  Diet Type
                </label>
                <select
                  id="dietType"
                  value={editedDietType}
                  onChange={(e) => setEditedDietType(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {DIET_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <Button onClick={handleSaveProfile} disabled={isSavingProfile}>
                  {isSavingProfile ? 'Saving...' : 'Save'}
                </Button>
                <Button variant="outline" onClick={cancelEditingProfile} disabled={isSavingProfile}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500">Email</p>
                <p className="text-sm">{user.email}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Full Name</p>
                <p className="text-sm">{user.full_name || 'Not set'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Diet Type</p>
                <p className="text-sm">{DIET_TYPE_LABELS[user.diet_type] || user.diet_type}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Account Status</p>
                <Badge variant={user.is_active ? 'default' : 'secondary'}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Member Since</p>
                <p className="text-sm">{formatDate(user.created_at)}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dietary Exclusions */}
      <Card aria-describedby="exclusions-desc">
        <CardHeader>
          <CardTitle>Dietary Exclusions</CardTitle>
          <CardDescription id="exclusions-desc">
            Select ingredients or categories to exclude from your meal plans.
            Changes will apply to future meal plans.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <ExclusionsListSkeleton />
          ) : (
            <>
              <div className="max-h-64 overflow-y-auto border rounded-md p-3 space-y-2">
                {availableExclusions.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-4">
                    No exclusion options available
                  </p>
                ) : (
                  availableExclusions.map((exclusion) => (
                    <label
                      key={exclusion.value}
                      className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selectedExclusions.includes(exclusion.value)}
                        onChange={() => toggleExclusion(exclusion.value)}
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm">{exclusion.name}</span>
                    </label>
                  ))
                )}
              </div>

              {selectedExclusions.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-sm text-gray-500">Selected:</span>
                  {selectedExclusions.map((value) => {
                    const exclusion = availableExclusions.find(e => e.value === value);
                    return (
                      <Badge key={value} variant="secondary">
                        {exclusion?.name || value}
                      </Badge>
                    );
                  })}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </Button>
                {hasChanges && (
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    disabled={isSaving}
                  >
                    Reset
                  </Button>
                )}
              </div>

              {hasChanges && (
                <p className="text-sm text-amber-600">
                  You have unsaved changes
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card aria-describedby="password-desc">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Password</CardTitle>
            <CardDescription id="password-desc">Change your account password</CardDescription>
          </div>
          {!isChangingPassword && (
            <Button variant="outline" size="sm" onClick={() => setIsChangingPassword(true)}>
              Change Password
            </Button>
          )}
        </CardHeader>
        {isChangingPassword && (
          <CardContent className="space-y-4">
            <div>
              <label htmlFor="currentPassword" className="text-sm font-medium text-gray-500 block mb-1">
                Current Password
              </label>
              <input
                id="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your current password"
              />
            </div>
            <div>
              <label htmlFor="newPassword" className="text-sm font-medium text-gray-500 block mb-1">
                New Password
              </label>
              <input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter new password (min 8 characters)"
              />
            </div>
            <div>
              <label htmlFor="confirmPassword" className="text-sm font-medium text-gray-500 block mb-1">
                Confirm New Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Confirm new password"
              />
            </div>
            <div className="flex gap-3">
              <Button
                onClick={handleChangePassword}
                disabled={isSavingPassword || !currentPassword || !newPassword || !confirmPassword}
              >
                {isSavingPassword ? 'Changing...' : 'Change Password'}
              </Button>
              <Button variant="outline" onClick={cancelChangePassword} disabled={isSavingPassword}>
                Cancel
              </Button>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Danger Zone - Delete Account */}
      <Card className="border-red-200" aria-describedby="danger-zone-desc">
        <CardHeader>
          <CardTitle className="text-red-600">Danger Zone</CardTitle>
          <CardDescription id="danger-zone-desc">
            Irreversible actions that will permanently affect your account.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!showDeleteConfirm ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Delete Account</p>
                <p className="text-sm text-gray-500">
                  Permanently delete your account and all associated data.
                </p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeleteConfirm(true)}
              >
                Delete Account
              </Button>
            </div>
          ) : (
            <div className="space-y-4 p-4 bg-red-50 rounded-md border border-red-200">
              <p className="text-sm text-red-800 font-medium">
                Are you sure you want to delete your account?
              </p>
              <p className="text-sm text-red-700">
                This action cannot be undone. All your data including meal plans and fridge items will be permanently deleted.
              </p>
              <div>
                <label htmlFor="deleteConfirm" className="text-sm font-medium text-red-700 block mb-1">
                  Type DELETE to confirm
                </label>
                <input
                  id="deleteConfirm"
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  className="w-full px-3 py-2 border border-red-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="DELETE"
                />
              </div>
              <div className="flex gap-3">
                <Button
                  variant="destructive"
                  onClick={handleDeleteAccount}
                  disabled={isDeleting || deleteConfirmText !== 'DELETE'}
                >
                  {isDeleting ? 'Deleting...' : 'Permanently Delete Account'}
                </Button>
                <Button variant="outline" onClick={cancelDeleteAccount} disabled={isDeleting}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
