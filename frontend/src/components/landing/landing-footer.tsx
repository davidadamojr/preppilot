export function LandingFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="py-8 bg-gray-50 border-t border-gray-100">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <p className="text-sm text-gray-500">
            &copy; {currentYear} PrepPilot. All rights reserved.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            PrepPilot is a concept in development.
          </p>
        </div>
      </div>
    </footer>
  );
}
