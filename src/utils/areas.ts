export const AREA_OPTIONS = [
  { value: 'HCM1', label: 'HCM 1' },
  { value: 'HCM4', label: 'HCM 4' },
]

export const AREA_CENTRES: Record<string, string[]> = {
  HCM1: ['Tô Ký', 'To Ky', 'Phan Văn Trị', 'Phan Van Tri', 'Phan Xích Long', 'Phan Xich Long'],
  HCM4: ['Tên Lửa', 'Ten Lua', 'Tây Thạnh', 'Tay Thanh', 'Lũy Bán Bích', 'Luy Ban Bich', 'Trường Chinh', 'Truong Chinh'],
}

export function centreMatchesArea(centre: string | null | undefined, area: string): boolean {
  if (!area) return true
  const centreName = centre ?? ''
  return AREA_CENTRES[area]?.some((keyword) => centreName.includes(keyword)) ?? true
}

export function filterCentresByArea(centres: string[], area: string): string[] {
  return area ? centres.filter((centre) => centreMatchesArea(centre, area)) : centres
}
