
export class TableBase {
    constructor(container_selector) {
        this.container = document.querySelector(container_selector);
        
        this.initialized = false;
        this.settings = {};
    }
    
    update() {
        throw new Error("method needs to be implemented for table");
    }
    
    on_control_change(name, value) {
        this.settings[name] = value;
        if (!this.initialized) return;
        this.update();
    }

    init() {
        this.container.classList.remove("wait");
        this.initialized = true;
        this.update();
    }
}