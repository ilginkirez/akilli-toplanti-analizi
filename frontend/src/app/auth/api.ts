import { request } from '../livekit-meeting/services/api';
import type { User } from '../types';


type ApiAuthUser = {
  id: string;
  name: string;
  email: string;
  avatar?: string | null;
  role?: User['role'];
  department?: string | null;
  company_id?: string | null;
  company_code?: string | null;
  company_name?: string | null;
  account_type?: string | null;
  status?: string | null;
};

type AuthResponse = {
  token: string;
  user: ApiAuthUser;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  name: string;
  email: string;
  password: string;
  department?: string;
  companyCode?: string;
  companyName?: string;
};

function normalizeRole(role?: string | null): User['role'] {
  return role === 'admin' || role === 'manager' ? role : 'member';
}

export function mapAuthUser(user: ApiAuthUser): User {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    avatar: user.avatar ?? undefined,
    role: normalizeRole(user.role),
    department: user.department ?? 'Genel',
    companyId: user.company_id ?? undefined,
    companyCode: user.company_code ?? undefined,
    companyName: user.company_name ?? undefined,
    accountType: user.account_type === 'company_member' ? 'company_member' : 'independent',
    status: user.status ?? undefined,
  };
}

export async function login(input: LoginRequest): Promise<{ token: string; user: User }> {
  const response = await request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email: input.email,
      password: input.password,
    }),
  });
  return {
    token: response.token,
    user: mapAuthUser(response.user),
  };
}

export async function register(input: RegisterRequest): Promise<{ token: string; user: User }> {
  const response = await request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      name: input.name,
      email: input.email,
      password: input.password,
      department: input.department,
      company_code: input.companyCode,
      company_name: input.companyName,
    }),
  });
  return {
    token: response.token,
    user: mapAuthUser(response.user),
  };
}

export async function me(): Promise<User> {
  const response = await request<ApiAuthUser>('/api/auth/me');
  return mapAuthUser(response);
}

export async function listCompanyMembers(query?: string): Promise<User[]> {
  const params = new URLSearchParams();
  if (query?.trim()) {
    params.set('q', query.trim());
  }
  const suffix = params.toString();
  const response = await request<{ users: ApiAuthUser[] }>(
    `/api/auth/company-members${suffix ? `?${suffix}` : ''}`,
  );
  return response.users.map(mapAuthUser);
}
