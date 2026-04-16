import { Button } from '../components/ui/button';
import { Link } from 'react-router';
import { Home, Search } from 'lucide-react';

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="mb-8">
        <div className="relative">
          <h1 className="text-9xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
            404
          </h1>
          <div className="absolute inset-0 blur-3xl bg-gradient-to-r from-blue-500/20 to-purple-600/20" />
        </div>
      </div>
      
      <div className="space-y-4 mb-8">
        <h2 className="text-3xl font-bold">Sayfa Bulunamadı</h2>
        <p className="text-gray-600 dark:text-gray-400 max-w-md">
          Aradığınız sayfa mevcut değil veya taşınmış olabilir. Lütfen URL'i kontrol edin veya ana sayfaya dönün.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Link to="/">
          <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
            <Home className="mr-2 h-4 w-4" />
            Ana Sayfaya Dön
          </Button>
        </Link>
        <Link to="/meetings">
          <Button variant="outline">
            <Search className="mr-2 h-4 w-4" />
            Toplantılara Git
          </Button>
        </Link>
      </div>
    </div>
  );
}
