export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#faf7f2]">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-[#1a1108] mb-4">Page Not Found</h1>
        <p className="text-[#7a6a58] mb-6">The page you're looking for doesn't exist.</p>
        <a 
          href="/" 
          className="inline-block px-6 py-3 bg-[#c8901e] text-[#1a1410] rounded-xl font-semibold hover:bg-[#a47c1a] transition-colors"
        >
          Go Home
        </a>
      </div>
    </div>
  );
}