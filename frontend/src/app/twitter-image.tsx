import { ImageResponse } from 'next/og';

export const runtime = 'edge';

export const alt = 'PrepPilot - Cook Fresh. Stay Safe.';
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = 'image/png';

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f0fdf4',
          backgroundImage: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 50%, #bbf7d0 100%)',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '40px 80px',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              marginBottom: '20px',
            }}
          >
            <div
              style={{
                width: '80px',
                height: '80px',
                borderRadius: '16px',
                backgroundColor: '#10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: '20px',
              }}
            >
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M6 13.87A4 4 0 0 1 7.41 6a5.11 5.11 0 0 1 1.05-1.54 5 5 0 0 1 7.08 0A5.11 5.11 0 0 1 16.59 6 4 4 0 0 1 18 13.87V21H6Z" />
                <line x1="6" y1="17" x2="18" y2="17" />
              </svg>
            </div>
            <span
              style={{
                fontSize: '64px',
                fontWeight: 'bold',
                color: '#166534',
              }}
            >
              PrepPilot
            </span>
          </div>
          <div
            style={{
              fontSize: '48px',
              fontWeight: 'bold',
              color: '#15803d',
              marginBottom: '20px',
              textAlign: 'center',
            }}
          >
            Cook Fresh. Stay Safe.
          </div>
          <div
            style={{
              fontSize: '28px',
              color: '#166534',
              textAlign: 'center',
              maxWidth: '900px',
              lineHeight: 1.4,
            }}
          >
            The first meal planner that tracks ingredient age in real-time
            for Low-Histamine & MAST cell diets
          </div>
          <div
            style={{
              display: 'flex',
              marginTop: '40px',
              gap: '30px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#dcfce7',
                padding: '12px 24px',
                borderRadius: '999px',
                fontSize: '20px',
                color: '#166534',
              }}
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                style={{ marginRight: '8px' }}
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Track Freshness
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#dcfce7',
                padding: '12px 24px',
                borderRadius: '999px',
                fontSize: '20px',
                color: '#166534',
              }}
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                style={{ marginRight: '8px' }}
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Reduce Waste
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#dcfce7',
                padding: '12px 24px',
                borderRadius: '999px',
                fontSize: '20px',
                color: '#166534',
              }}
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                style={{ marginRight: '8px' }}
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Stay Healthy
            </div>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
