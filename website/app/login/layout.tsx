export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Don't wrap with OidcProvider here - it's already in root layout
  // Just provide the centered container styling
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      {children}
    </div>
  );
}
