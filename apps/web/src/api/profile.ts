import { api } from "./client"

export interface ProfileData {
  user: {
    id: string
    name: string
    email: string
    avatar?: string
    watchlist: number[]
    history: {
      id: number
      progress: number
      lastWatched: string
    }[]
  }
}

export async function getProfileData() {
  return api.get<ProfileData>("/profile")
}

export async function updateProfile(data: Partial<ProfileData["user"]>) {
  return api.post<ProfileData>("/profile/update", data)
}
