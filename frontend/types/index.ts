// User, Trip, Message, ChatResponse 等类型
export interface User {
  id: number;
  username: string;
  created_at: string;
}

export interface Trip {
  id: number;
  user_id: number;
  title: string;
  plan_data: PlanData | null;
  status: "draft" | "confirmed";
  created_at: string;
  updated_at: string;
}

export interface PlanData {
  destination: string;
  duration: number;
  budget: number;
  style: string[];
  overview: string;
  days: DayPlan[];
  overall_tips: string;
}

export interface DayPlan {
  day: number;
  date: string | null;
  theme: string;
  attractions: Attraction[];
  meals: Meal[];
}

export interface Attraction {
  name: string;
  type: string;
  duration_minutes: number;
  cost_yuan: number;
  tips: string;
  transport_from_previous: string | null;
}

export interface Meal {
  meal_type: string;
  suggestion: string;
  location_near: string;
}

export interface Message {
  id: number;
  trip_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

/** SSE 事件类型 */
export type SSEEvent =
  | { type: "token"; content: string }
  | { type: "done"; data: { trip_id?: number } }
  | { type: "error"; detail: string };

/** 登录/注册返回值 */
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** GET /api/trips 返回值 */
export interface TripListResponse {
  trips: Trip[];
  total: number;
  page: number;
  page_size: number;
}

/** sendMessage 回调集合 */
export interface SSEHandlers {
  onToken?: (text: string) => void;
  onDone?: (tripId?: number) => void;
  onError?: (err: string) => void;
}

/** PATCH /api/trips/{id} 请求体 */
export interface TripUpdateRequest {
  title?: string;
  status?: string;
}
