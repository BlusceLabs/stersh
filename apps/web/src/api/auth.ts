import { api } from "./client"

export interface User {
  id: string
  email: string
  name: string
  avatar?: string
}

export async function login(email: string, password: string) {
  return api.post<User>("/auth/login", { email, password })
}

export async function register(email: string, password: string, name: string) {
  return api.post<User>("/auth/register", { email, password, name })
}

export async function getProfile() {
  return api.get<User>("/auth/profile")
}

export async function logout() {
  return api.post("/auth/logout")
}
