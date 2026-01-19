import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: ["class"],
    content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
  	extend: {
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			},
  			sage: {
  				50: 'hsl(var(--sage-50))',
  				100: 'hsl(var(--sage-100))',
  				200: 'hsl(var(--sage-200))',
  				300: 'hsl(var(--sage-300))',
  				400: 'hsl(var(--sage-400))',
  				500: 'hsl(var(--sage-500))',
  				600: 'hsl(var(--sage-600))',
  				700: 'hsl(var(--sage-700))',
  				800: 'hsl(var(--sage-800))',
  				900: 'hsl(var(--sage-900))'
  			},
  			alert: {
  				50: 'hsl(var(--alert-50))',
  				100: 'hsl(var(--alert-100))',
  				200: 'hsl(var(--alert-200))',
  				300: 'hsl(var(--alert-300))',
  				400: 'hsl(var(--alert-400))',
  				500: 'hsl(var(--alert-500))',
  				600: 'hsl(var(--alert-600))',
  				700: 'hsl(var(--alert-700))',
  				800: 'hsl(var(--alert-800))',
  				900: 'hsl(var(--alert-900))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
