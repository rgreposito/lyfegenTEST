import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from '../App';

// Mock the API services
jest.mock('../services/api', () => ({
  documentApi: {
    list: jest.fn(),
    upload: jest.fn(),
    delete: jest.fn(),
    search: jest.fn(),
    getTypes: jest.fn(),
  },
  chatApi: {
    createSession: jest.fn(),
    getSession: jest.fn(),
    sendMessage: jest.fn(),
    getSummary: jest.fn(),
    getSuggestions: jest.fn(),
    deleteSession: jest.fn(),
    listSessions: jest.fn(),
  },
  healthApi: {
    check: jest.fn(),
  },
}));

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('App Component', () => {
  test('renders without crashing', () => {
    renderWithRouter(<App />);
    expect(screen.getByText(/Document AI/i)).toBeInTheDocument();
  });

  test('renders navigation menu', () => {
    renderWithRouter(<App />);
    expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Upload/i)).toBeInTheDocument();
    expect(screen.getByText(/Documents/i)).toBeInTheDocument();
    expect(screen.getByText(/Chat/i)).toBeInTheDocument();
  });

  test('renders welcome message on dashboard', () => {
    renderWithRouter(<App />);
    expect(screen.getByText(/Welcome to Document AI/i)).toBeInTheDocument();
  });
});