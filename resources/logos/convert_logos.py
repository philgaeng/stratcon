#!/usr/bin/env python3
"""
Logo Conversion Utility
Converts PNG logos to base64 format for embedding in HTML reports
"""

import base64
import os
import json

def convert_logos_to_base64():
    """Convert all PNG logos to base64 format"""
    logos_dir = "/home/philg/projects/stratcon/resources/logos"
    os.chdir(logos_dir)
    
    # Logo mapping
    logo_mapping = {
        "white": "Stratcon.ph White.png",
        "black": "Stratcon.ph Black.png", 
        "full_color": "Stratcon.ph Full Color3.png",
        "brandmark": "Stratcon Brandmark.png"
    }
    
    results = {}
    
    print("🎨 Converting Stratcon logos to base64 format...")
    print("=" * 50)
    
    for logo_type, filename in logo_mapping.items():
        try:
            if os.path.exists(filename):
                # Read the logo file
                with open(filename, 'rb') as f:
                    logo_data = f.read()
                
                # Convert to base64
                base64_logo = base64.b64encode(logo_data).decode('utf-8')
                
                # Create data URI
                data_uri = f'data:image/png;base64,{base64_logo}'
                
                # Save to text file
                output_file = f"{logo_type}_logo_base64.txt"
                with open(output_file, 'w') as f:
                    f.write(data_uri)
                
                results[logo_type] = {
                    "filename": filename,
                    "base64_file": output_file,
                    "size_bytes": len(logo_data),
                    "base64_length": len(base64_logo),
                    "data_uri": data_uri[:100] + "..." if len(data_uri) > 100 else data_uri
                }
                
                print(f"✅ {logo_type.upper()}: {filename}")
                print(f"   📁 Output: {output_file}")
                print(f"   📊 Size: {len(logo_data):,} bytes → {len(base64_logo):,} chars")
                print()
                
            else:
                print(f"❌ {logo_type.upper()}: {filename} not found")
                
        except Exception as e:
            print(f"❌ Error processing {logo_type}: {e}")
    
    # Save results to JSON for reference
    with open("logo_conversion_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print("=" * 50)
    print(f"🎉 Conversion complete! {len(results)} logos processed.")
    print("📄 Results saved to: logo_conversion_results.json")
    
    return results

if __name__ == "__main__":
    convert_logos_to_base64()
