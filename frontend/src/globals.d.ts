declare global {
  interface Window {
    config: {
      cspr_click_app_name: string;
      cspr_click_app_id: string;
      cspr_click_providers: string[];
      cspr_live_url: string;
    };
  }
}

declare const config: {
  cspr_click_app_name: string;
  cspr_click_app_id: string;
  cspr_click_providers: string[];
  cspr_live_url: string;
};

export {};
