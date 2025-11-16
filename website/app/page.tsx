import { redirect } from 'next/navigation';

export default function Home() {
  // Redirect to login page for now
  // TODO: Add authentication check and redirect to /reports if authenticated
  redirect('/login');
}
