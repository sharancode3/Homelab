let inMemoryToken: string | null = null;

export const setToken = (token: string | null) => {
  inMemoryToken = token;
};

export const getToken = () => {
  return inMemoryToken;
};
