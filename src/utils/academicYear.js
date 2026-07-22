export const ACADEMIC_YEAR_START_MONTH = 9;

export const getDefaultAcademicYear = (date = new Date()) => {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  return month >= ACADEMIC_YEAR_START_MONTH ? year : year - 1;
};

export const buildAcademicYearOptions = (
  baseYear = getDefaultAcademicYear(),
  before = 2,
  after = 2
) => {
  const years = [];
  for (let i = -before; i <= after; i += 1) {
    years.push(baseYear + i);
  }
  return years.sort((a, b) => b - a);
};
