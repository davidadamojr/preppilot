import { NextRequest, NextResponse } from 'next/server';

const FORMSPREE_FORM_ID = process.env.FORMSPREE_FORM_ID;

function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email } = body;

    if (!email || typeof email !== 'string') {
      return NextResponse.json({ error: 'Email is required' }, { status: 400 });
    }

    if (!isValidEmail(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    if (!FORMSPREE_FORM_ID) {
      console.error('FORMSPREE_FORM_ID not configured');
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    const formspreeResponse = await fetch(
      `https://formspree.io/f/${FORMSPREE_FORM_ID}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({ email }),
      }
    );

    if (!formspreeResponse.ok) {
      const errorData = await formspreeResponse.json();
      console.error('Formspree error:', errorData);
      return NextResponse.json(
        { error: 'Failed to submit email' },
        { status: 502 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Waitlist submission error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
